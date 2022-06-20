import logging
import json
import solardatatools
import pandas as pd
import boto3
import time
from os.path import exists
from datetime import datetime

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)
from decimal import Decimal
import enum


class Alert(enum.Enum):
    PROCESS_FILE_ERROR = "PROCESS_FILE_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT = "TIMEOUT"
    SAVED_DATA = "SAVED_DATA"


def make_response(subject: str = None, messages: dict = None) -> dict:
    if subject is None:
        subject = Alert.SYSTEM_ERROR.name
        messages = "No subject in sns message"
        raise Exception("Message Input Error")
    # message_str = json.dumps(messages)
    if not isinstance(messages, dict):
        raise Exception("messages is not a json object")
    response = {"Subject": subject, "Messages": messages}
    return response


def read_csv_from_s3_with_column_and_time(
    bucket_name: str = None,
    file_path_name: str = None,
    column_name: str = None,
    index_col: int = 0,
    parse_dates=[0],
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> pd.DataFrame:
    """
    Read csv file from s3 bucket with define column , and time column.
    :param : bucket_name
    :param : file_path_name
    :param : column_name
    :param : index_col, column of index
    :param : parse_dates, column of time
    :param : aws_access_key
    :param : aws_secret_access_key
    :param : aws_region
    :return: dataframe.
    """

    if (
        bucket_name is None
        or file_path_name is None
        or column_name is None
        or aws_access_key is None
        or aws_secret_access_key is None
        or aws_region is None
    ):
        return
    try:
        s3_client = boto3.client(
            "s3",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
        )
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status != 200:
            return Exception(f"Unsuccessful S3 get_object response. Status - {status}")

        result_df = pd.read_csv(
            response.get("Body"),
            index_col=index_col,
            parse_dates=parse_dates,
            usecols=["Time", column_name],
        )
        return result_df
    except Exception as e:
        raise Exception(f"Read csv fialed:{e}")


def entrypoint(
    data_bucket: str = None,
    curr_process_file: str = None,
    curr_process_column: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    solver_name: str = None,
    solver_file: str = None,
) -> dict:
    # logger.info("----- This is template code.")
    logger.info(
        f"process file:{curr_process_file} , column:{curr_process_column}, solve: {solver_file}"
    )

    # check solver file :
    if solver_name is not None and (exists(solver_file) is False):
        return Exception(f"solver_file:{solver_file} dose not exist")

    # read csv file from s3
    try:
        df = read_csv_from_s3_with_column_and_time(
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
        dh = solardatatools.DataHandler(df)
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

        # save data as json format
        save_data = {
            "bucket": f"{data_bucket}",
        }

    except Exception as e:
        raise Exception(f"Save data error: {e}")
    # length =float("{:.1f}".format(0.9* 1))
    # save_data = {"length":length}
    return make_response(subject=Alert.SAVED_DATA.name, messages=save_data)
