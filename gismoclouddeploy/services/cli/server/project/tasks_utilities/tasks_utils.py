import botocore
from matplotlib import use
from utils.aws_utils import (
    connect_aws_client,
    connect_aws_resource,
    download_solver_licence_from_s3_and_save,
)
import socket
import json


import pandas as pd
from os.path import exists

from models.LogsInfo import LogsInfo

import os


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
            "user_id": LogsInfo.user_id,
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


# def put_item_to_dynamodb(
#     table_name: str,
#     LogsInfo: LogsInfo,
#     aws_access_key: str,
#     aws_secret_access_key: str,
#     aws_region: str,
# ):
#     dynamodb_resource = connect_aws_resource(
#         resource_name="dynamodb",
#         key_id=aws_access_key,
#         secret=aws_secret_access_key,
#         region=aws_region,
#     )
#     table = dynamodb_resource.Table(table_name)
#     response = table.put_item(
#         Item={
#             "user":LogsInfo.user,
#             "host_name": LogsInfo.host_name,
#             "host_ip": LogsInfo.host_ip,
#             "task_id": str(LogsInfo.task_id),
#             "pid": LogsInfo.pid,
#             "function_name": LogsInfo.function_name,
#             "action": LogsInfo.action,
#             "timestamp": LogsInfo.time,
#             "message": LogsInfo.message,
#             "filename": LogsInfo.filename,
#             "column_name": LogsInfo.column_name,
#         }
#     )
#     return response


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
        logger.info(f"----- Publish subject {subject} message {message}")
        # logger.info(
        #     # f"Message published to topic - {topic_arn} with message Id - {message_id}."
        # )
        return message_id
    except Exception as e:
        logger.error(f"publish message fail : {e}")
        raise e


def check_and_download_solver(
    solver_name: str = None,
    slover_lic_file_name: str = None,
    solver_lic_target_path: str = None,
    saved_solver_bucket: str = None,
    saved_temp_path_in_bucket: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:
    if solver_name is None:
        logger.info("No solver name is specified")
        return
    # check if the file is exist in local directory
    local_solver_file = solver_lic_target_path + "/" + slover_lic_file_name
    if exists(local_solver_file) is False:
        logger.info(
            f"No solver in worker image. Download MOSEK Licence from {saved_solver_bucket} {saved_temp_path_in_bucket}"
        )
        try:
            s3_client = connect_aws_client(
                "s3",
                key_id=aws_access_key,
                secret=aws_secret_access_key,
                region=aws_region,
            )
            file_path_name = saved_temp_path_in_bucket + "/" + slover_lic_file_name
            download_solver_licence_from_s3_and_save(
                s3_client=s3_client,
                bucket_name=saved_solver_bucket,
                file_path_name=file_path_name,
                saved_file_path=solver_lic_target_path,
                saved_file_name=slover_lic_file_name,
            )
            logger.info("=========== Download solver success ============== ")
            return
        except Exception as e:
            logger.error(
                f"Cannot download solver{solver_name} from {saved_solver_bucket}::{saved_temp_path_in_bucket}/{slover_lic_file_name}"
            )
            raise f"Cannot download solver{solver_name} from {saved_solver_bucket}::{saved_temp_path_in_bucket}/{slover_lic_file_name}"
    logger.info(f"{local_solver_file} exists")
    return
    #


def track_logs(
    task_id: str,
    user_id: str,
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
        user_id=user_id,
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


def make_response(subject: str = None, messages: str = None) -> dict:
    response = {"Subject": subject, "Messages": messages}
    return response


def parse_subject_from_response(response: dict, task_id: str) -> str:
    # response["Subject"]['task_id'] = task_id
    # sub = str(response["Subject"]).strip("'<>() ").replace("'", '"').strip("\n")
    # subject = json.loads(sub)
    # print("---------------->>>>")
    # subject['task_id'] = str(task_id)

    # print(f"subject :{subject}")
    try:
        return str(response["Subject"])
        # subject_str = json.dumps(subject)
    except Exception as e:
        logger.error(f"===>dumps to json error:{e} ")
        raise e
    return subject_str


def parse_messages_from_response(response: dict) -> str:
    try:

        return str(response["Messages"])
    except Exception as e:
        raise e


# def append_taskid_to_message(response: dict, task_id: str = None) -> str:
#     if not isinstance(response, dict):
#         raise Exception("response is not a json object")
#     try:
#         json_obj = json.loads(response)
#         json_obj["Messages"]["task_id"] = task_id
#         return json_obj
#     except Exception as e:
#         logger.info("-------------------------")
#         logger.error("append task id error")
#         raise e
