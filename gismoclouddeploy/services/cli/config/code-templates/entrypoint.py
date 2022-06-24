import imp
import logging
import json
from solardatatools.data_handler import DataHandler

from os.path import exists
from datetime import datetime
from .my_modules import read_csv_from_s3, Alert, make_response

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def entrypoint(
    user_id: str = None,
    data_bucket: str = None,
    curr_process_file: str = None,
    curr_process_column: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    solver_name: str = None,
    solver_file: str = None,
) -> dict:
    """
    Entrypoint function to wrap your code
    :param str user_id: This user_id is generated in cli command and pass to here(worker). This user id is required to used in sns, dynamodb and sqs services
    :param str data_bucket: This data_bucket is the s3 bucket that contains data files.
    :param str curr_process_file: Current process file. This file name is one of the column name in logs file.()
    :param str curr_process_column: Current proccess column name. This column name is one of the column name in logs file.
    :param str aws_access_key:
    :param str aws_secret_access_key:
    :param str aws_region:
    :param str solver_name: The solver name that defined in config.yaml
    :param str solver_file: The solver file location inside worker. This file location is defined in config.yaml.
    :return dict json_message: Return a json format object contain user_id (This message is used to publish sns message and track logs in dynamodb)
    """

    ## ==================== Modify your code below ==================== ##
    logger.info(
        f"process file:{curr_process_file} , column:{curr_process_column}, solve: {solver_file}"
    )

    # check solver file exist: The download function is inside `check_and_download_solver` function ""
    if solver_name is not None and (exists(solver_file) is False):
        return Exception(f"solver_file:{solver_file} dose not exist")

    # read csv file from s3
    try:
        df = read_csv_from_s3(
            bucket_name=data_bucket,
            file_path_name=curr_process_file,
            column_name=curr_process_column,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
    except Exception as e:
        logger.error(f"Read column and time error: {e}")
        raise e

    try:
        dh = DataHandler(df)
        logger.info(f"run solardatatools pipeline solver: {solver_name}")
        dh.run_pipeline(
            power_col=curr_process_column,
            min_val=-5,
            max_val=None,
            zero_night=True,
            interp_day=True,
            fix_shifts=True,
            density_lower_threshold=0.6,
            density_upper_threshold=1.05,
            linearity_threshold=0.1,
            clear_day_smoothness_param=0.9,
            clear_day_energy_param=0.8,
            verbose=False,
            start_day_ix=None,
            end_day_ix=None,
            c1=None,
            c2=500.0,
            solar_noon_estimator="com",
            correct_tz=True,
            extra_cols=None,
            daytime_threshold=0.1,
            units="W",
            solver=solver_name,
        )
    except Exception as e:
        raise Exception(f"Run run_pipeline fail:{e}")

    try:
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

        ## ==================== Save data in json format is required  your code above ==================== ##

        save_data = {
            "bucket": data_bucket,
            "file": curr_process_file,
            "column": curr_process_column,
            "solver": solver_name,
            "length": length,
            "capacity_estimate": capacity_estimate,
            "power_units": power_units,
            "data_sampling": data_sampling,
            "data_quality_score": data_quality_score,
            "data_clearness_score": data_clearness_score,
            "time_shifts": time_shifts,
            "num_clip_points": num_clip_points,
            "tz_correction": tz_correction,
            "inverter_clipping": inverter_clipping,
            "normal_quality_scores": normal_quality_scores,
            "capacity_changes": capacity_changes,
        }
    except Exception as e:
        raise Exception(f"Save data error: {e}")

    ## ==================== Modify your code above ==================== ##

    return make_response(
        alert_type=Alert.SAVED_DATA.name,
        messages=save_data,
        user_id=user_id,
    )
