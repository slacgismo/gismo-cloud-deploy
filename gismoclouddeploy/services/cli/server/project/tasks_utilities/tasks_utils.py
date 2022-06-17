from ast import Str
from cmath import log
import botocore
from utils.aws_utils import (
    connect_aws_client,
    connect_aws_resource,
    to_s3,
    read_csv_from_s3,
    download_solver_licence_from_s3_and_save,
)
import socket
import copy
import json

from project.solardata.solardata_models import SolarData, SolarParams

# from project.solardata.models.SolarParams import SolarParams

import pandas as pd
from os.path import exists

# from project.solardata.models.SolarData import SolarData
from models.LogsInfo import LogsInfo

import os
from io import StringIO

from boto3.dynamodb.types import TypeDeserializer
from typing import List
import logging

from typing import Set

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def put_item_to_dynamodb(
    table_name: str,
    LogsInfo: LogsInfo,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
):
    dynamodb_resource = connect_aws_resource(
        resource_name="dynamodb",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    table = dynamodb_resource.Table(table_name)
    response = table.put_item(
        Item={
            "host_name": LogsInfo.host_name,
            "host_ip": LogsInfo.host_ip,
            "task_id": str(LogsInfo.task_id),
            "pid": LogsInfo.pid,
            "function_name": LogsInfo.function_name,
            "action": LogsInfo.action,
            "timestamp": LogsInfo.time,
            "message": LogsInfo.message,
            "filename": LogsInfo.filename,
            "column_name": LogsInfo.column_name,
        }
    )
    return response


def publish_message_sns(
    message: str,
    subject: str,
    topic_arn: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> str:
    try:
        sns_client = connect_aws_client(
            client_name="sns",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )

        message_res = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
        message_id = message_res["MessageId"]
        logger.info(
            f"Message published to topic - {topic_arn} with message Id - {message_id}."
        )
        return message_id
    except Exception as e:
        logger.error(f"publish message fail : {e}")
        raise e


def check_solver_licence(
    solarParams: SolarParams = None, s3_client: "botocore.client.S3" = None
) -> None:
    if solarParams.solver_name is None:
        raise Exception("No solver name")

    # check if the file is exist in local directory
    solver_target_file_path = (
        solarParams.solver_saved_lic_file_path
        + "/"
        + solarParams.solver_saved_lic_file_name
    )
    if exists(solver_target_file_path) is False:
        logger.info(
            f"Download MOSEK Licence {solarParams.solver_lic_file_path_name} from {solarParams.solver_lic_bucket}"
        )
        try:
            download_solver_licence_from_s3_and_save(
                s3_client=s3_client,
                bucket_name=solarParams.solver_lic_bucket,
                file_path_name=solarParams.solver_lic_file_path_name,
                saved_file_path=solarParams.solver_saved_lic_file_path,
                saved_file_name=solarParams.solver_saved_lic_file_name,
            )
        except Exception as e:
            raise e


def str_to_bool(s: str):

    if type(s) == type(True):
        return s

    if type(s) != str:
        raise TypeError

    if s == "True":
        return True
    elif s == "False":
        return False
    else:
        raise ValueError


def make_solardata_params_obj_from_json(algorithm_json: str) -> SolarParams:
    try:

        solar_params_json = algorithm_json["solar_data_tools"]

        power_col = str(solar_params_json["power_col"])
        min_val = solar_params_json["min_val"]
        if min_val == "None":
            min_val = None
        else:
            min_val = int(solar_params_json["min_val"])

        max_val = solar_params_json["max_val"]
        if max_val == "None":
            max_val = None
        else:
            max_val = int(solar_params_json["max_val"])

        zero_night = str_to_bool(solar_params_json["zero_night"])
        interp_day = str_to_bool(solar_params_json["interp_day"])
        fix_shifts = str_to_bool(solar_params_json["fix_shifts"])

        density_lower_threshold = float(solar_params_json["density_lower_threshold"])
        density_upper_threshold = float(solar_params_json["density_upper_threshold"])
        linearity_threshold = float(solar_params_json["linearity_threshold"])
        clear_day_smoothness_param = float(
            solar_params_json["clear_day_smoothness_param"]
        )
        clear_day_energy_param = float(solar_params_json["clear_day_energy_param"])
        verbose = str_to_bool(solar_params_json["verbose"])

        start_day_ix = solar_params_json["start_day_ix"]
        if start_day_ix == "None":
            start_day_ix = None
        else:
            start_day_ix = int(solar_params_json["start_day_ix"])

        end_day_ix = solar_params_json["end_day_ix"]
        if end_day_ix == "None":
            end_day_ix = None
        else:
            end_day_ix = int(solar_params_json["end_day_ix"])

        c1 = solar_params_json["c1"]
        if c1 == "None":
            c1 = None
        else:
            c1 = float(solar_params_json["c1"])

        c2 = solar_params_json["c2"]
        if c2 == "None":
            c2 = None
        else:
            c2 = float(solar_params_json["c2"])

        solar_noon_estimator = str(solar_params_json["solar_noon_estimator"])
        correct_tz = str_to_bool(solar_params_json["correct_tz"])
        extra_cols = str(solar_params_json["extra_cols"])

        extra_cols = solar_params_json["extra_cols"]
        if extra_cols == "None":
            extra_cols = None
        else:
            extra_cols = str(solar_params_json["extra_cols"])

        daytime_threshold = float(solar_params_json["daytime_threshold"])
        units = str(solar_params_json["units"])

        solver = solar_params_json["solver"]

        if solver == "None":
            solver = None
        else:
            solver_name = solver["name"]
            solver_lic_bucket = solver["lic_bucket"]
            solver_lic_file_path_name = solver["lic_file_path_name"]
            solver_saved_lic_file_path = solver["lic_saved_target_path"]
            solver_saved_lic_file_name = solver["lic_saved_target_name"]

        solarparams = SolarParams(
            power_col,
            min_val,
            max_val,
            zero_night,
            interp_day,
            fix_shifts,
            density_lower_threshold,
            density_upper_threshold,
            linearity_threshold,
            clear_day_smoothness_param,
            clear_day_energy_param,
            verbose,
            start_day_ix,
            end_day_ix,
            c1,
            c2,
            solar_noon_estimator,
            correct_tz,
            extra_cols,
            daytime_threshold,
            units,
            solver,
            solver_name=solver_name,
            solver_lic_bucket=solver_lic_bucket,
            solver_lic_file_path_name=solver_lic_file_path_name,
            solver_saved_lic_file_path=solver_saved_lic_file_path,
            solver_saved_lic_file_name=solver_saved_lic_file_name,
        )

        return solarparams
    except Exception as e:
        print(f"conver solardata parameter error :{e}")
        raise e


def track_logs(
    task_id: str,
    function_name: str,
    time: str,
    action: str,
    message: str,
    process_file_name: str,
    table_name: str,
    column_name: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
):

    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)
    pid = os.getpid()
    start_status = LogsInfo(
        host_name=hostname,
        task_id=task_id,
        host_ip=host_ip,
        pid=str(pid),
        function_name=function_name,
        action=action,
        time=time,
        message=message,
        filename=process_file_name,
        column_name=column_name,
    )

    put_item_to_dynamodb(
        table_name=table_name,
        LogsInfo=start_status,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
    )


# def list_files_in_folder_of_bucket(
#     bucket_name: str, file_path: str, s3_client: "botocore.client.S3"
# ) -> List[str]:
#     """Get filename from a folder of the bucket , remove non csv file"""

#     response = s3_client.list_objects_v2(Bucket=bucket_name)
#     files = response["Contents"]
#     filterFiles = []
#     for file in files:
#         split_tup = os.path.splitext(file["Key"])
#         path, filename = os.path.split(file["Key"])
#         file_extension = split_tup[1]
#         if file_extension == ".csv" and path == file_path:
#             filterFiles.append(file["Key"])
#     return filterFiles


def make_response(subject: str = None, messages: str = None) -> dict:
    response = {"Subject": subject, "Messages": messages}
    return response


def parse_subject_from_response(response: dict) -> str:
    try:
        return str(response["Subject"])
    except Exception as e:
        raise e


def parse_messages_from_response(response: dict) -> str:
    try:

        return str(response["Messages"])
    except Exception as e:
        raise e


def append_taskid_to_message(response: dict, task_id: str = None) -> str:
    if not isinstance(response, dict):
        raise Exception("response is not a json object")
    try:
        json_obj = json.loads(response)
        json_obj["Messages"]["task_id"] = task_id
        return json_obj
    except Exception as e:
        logger.info("-------------------------")
        logger.error("append task id error")
        raise e
