# from project.solardatatools.models.SolarParams import SolarParams
# from project.solardatatools.models.SolarData import SolarData
import solardatatools
import socket
from datetime import datetime

# from project.utils.tasks_utils import (
#     save_solardata_to_file,
#     check_solver_licence,

# )
# from utils.aws_utils import (
#     read_csv_from_s3_with_column_and_time,
#     connect_aws_client,
# )
# import solardata_models
# import utils.aws_utils
# import project.utils.tasks_utils
from .solardata_models import SolarData, SolarParams
from utils import aws_utils
from project.tasks_utilities import tasks_utils
import logging
import time


# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def entrypoint(
    task_id: str = None,
    bucket_name: str = None,
    file_path_name: str = None,
    column_name: str = None,
    start_time: str = None,
    saved_bucket: str = None,
    saved_file_path: str = None,
    saved_filename: str = None,
    solarParams: SolarParams = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> str:

    """
    Process solardatatools from file with specific column name
    :param : task id
    :param : bucket_name
    :param : file_path_name
    :param : column_name
    :param : start_time
    :param : saved_bucket
    :param : saved_file_path
    :param : saved_filename
    :param : solarParams. -> solardatatools parameters object
    :return: success messages.
    """
    if (
        bucket_name is None
        or file_path_name is None
        or column_name is None
        or saved_bucket is None
        or solarParams is None
    ):
        raise Exception("Input error")
    error_message = ""
    try:
        s3_client = aws_utils.connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
    except Exception as e:
        logger.error(f"Connect to AWS error: {e}")
        raise e

    # check solver
    try:
        tasks_utils.check_solver_licence(solarParams=solarParams, s3_client=s3_client)
    except Exception as e:
        logger.error(f"Check solver error: {e}")
        raise e

    # read csv file from s3
    try:
        df = aws_utils.read_csv_from_s3_with_column_and_time(
            bucket_name=bucket_name,
            file_path_name=file_path_name,
            column_name=column_name,
            s3_client=s3_client,
        )
    except Exception as e:
        error_message += f"read column and time error: {e}"
        logger.error(f"read column and time error: {e}")
        raise e

    solarParams.power_col = column_name

    try:
        dh = solardatatools.DataHandler(df)
        logger.info(f"run ======== code ===============: {solarParams.solver_name}")
        logger.info(f"run solardatatools pipeline solver: {solarParams.solver_name}")
        dh.run_pipeline(
            power_col=column_name,
            min_val=solarParams.min_val,
            max_val=solarParams.max_val,
            zero_night=solarParams.zero_night,
            interp_day=solarParams.interp_day,
            fix_shifts=solarParams.fix_shifts,
            density_lower_threshold=solarParams.density_lower_threshold,
            density_upper_threshold=solarParams.density_upper_threshold,
            linearity_threshold=solarParams.linearity_threshold,
            clear_day_smoothness_param=solarParams.clear_day_smoothness_param,
            clear_day_energy_param=solarParams.clear_day_energy_param,
            verbose=solarParams.verbose,
            start_day_ix=solarParams.start_day_ix,
            end_day_ix=solarParams.end_day_ix,
            c1=solarParams.c1,
            c2=solarParams.c2,
            solar_noon_estimator=solarParams.solar_noon_estimator,
            correct_tz=solarParams.correct_tz,
            extra_cols=solarParams.extra_cols,
            daytime_threshold=solarParams.daytime_threshold,
            units=solarParams.units,
            solver=solarParams.solver_name,
        )
        length = float("{:.2f}".format(dh.num_days))
        if dh.num_days >= 365:
            length = float("{:.2f}".format(dh.num_days / 365))

        capacity_estimate = float("{:.2f}".format(dh.capacity_estimate))

        power_units = str(dh.power_units)
        if power_units == "W":
            capacity_estimate = float("{:.2f}".format(dh.capacity_estimate / 1000))
        data_sampling = int(dh.data_sampling)

        if dh.raw_data_matrix.shape[0] > 1440:
            data_sampling = int(dh.data_sampling * 60)

        data_quality_score = float("{:.1f}".format(dh.data_quality_score * 100))
        data_clearness_score = float("{:.1f}".format(dh.data_clearness_score * 100))
        time_shifts = bool(dh.time_shifts)
        num_clip_points = int(dh.num_clip_points)
        tz_correction = int(dh.tz_correction)
        inverter_clipping = bool(dh.inverter_clipping)
        normal_quality_scores = bool(dh.normal_quality_scores)
        capacity_changes = bool(dh.capacity_changes)
        end_time = time.time()
        process_time = float(end_time) - float(start_time)
        end_time_date = datetime.fromtimestamp(end_time)
        start_time_date = datetime.fromtimestamp(start_time)

        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)

        # save process result to s3 file
        solarData = SolarData(
            task_id=task_id,
            hostname=hostname,
            host_ip=host_ip,
            stat_time=start_time_date,
            end_time=end_time_date,
            bucket_name=bucket_name,
            file_path_name=file_path_name,
            column_name=column_name,
            process_time=process_time,
            length=length,
            power_units=power_units,
            capacity_estimate=capacity_estimate,
            data_sampling=data_sampling,
            data_quality_score=data_quality_score,
            data_clearness_score=data_clearness_score,
            error_message=error_message,
            time_shifts=time_shifts,
            capacity_changes=capacity_changes,
            num_clip_points=num_clip_points,
            tz_correction=tz_correction,
            inverter_clipping=inverter_clipping,
            normal_quality_scores=normal_quality_scores,
        )

        tasks_utils.save_solardata_to_file(
            solardata=solarData.to_json(),
            saved_bucket=saved_bucket,
            saved_file_path=saved_file_path,
            saved_filename=saved_filename,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )

        return f"Success process file {file_path_name}: column :{column_name}"

    except Exception as e:
        error_message += str(e)
        logger.error(f"Run solar data tools error {e}")
        raise e
