from copy import copy
from distutils.log import error
import json
import sys
import boto3
import copy
import functools
import time
import os
import socket
from .tasks_utils import (
    publish_message_sns,
    check_and_download_solver,
)

import logging
from models.WorkerState import WorkerState
from models.SNSSubjectsAlert import SNSSubjectsAlert


logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def tracklog_decorator(func):
    """custom decorator"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """updates special attributes e.g. __name__,__doc__"""
        try:
            task_id = args[0].request.id
            table_name = kwargs["dynamodb_tablename"]
            curr_process_file = kwargs["curr_process_file"]
            curr_process_column = kwargs["curr_process_column"]
            solver = kwargs["solver"]
            aws_access_key = kwargs["aws_access_key"]
            aws_secret_access_key = kwargs["aws_secret_access_key"]
            aws_region = kwargs["aws_region"]
            sns_topic = kwargs["sns_topic"]
            user_id = kwargs["user_id"]

        except Exception as e:
            raise Exception(f"Decorator Input key errir:{e}")
        start_time = str(time.time())
        # fire task start sns
        # init_message = make_sns_response(
        #     alert_type=SNSSubjectsAlert.TASK_START.name,
        #     messages={
        #         "start_time": start_time,
        #         "task_id": str(task_id),
        #         "file": curr_process_file,
        #         "column": curr_process_column,
        #     },
        #     user_id=user_id,
        # )
        # publish_message_sns(
        #     message=json.dumps(init_message["Messages"]),
        #     subject=json.dumps(init_message["Subject"]),
        #     topic_arn=sns_topic,
        #     aws_access_key=aws_access_key,
        #     aws_secret_access_key=aws_secret_access_key,
        #     aws_region=aws_region,
        # )
        try:
            check_and_download_solver(
                solver_name=solver["solver_name"],
                slover_lic_file_name=solver["solver_lic_file_name"],
                solver_lic_target_path=solver["solver_lic_target_path"],
                saved_solver_bucket=solver["saved_solver_bucket"],
                saved_temp_path_in_bucket=solver["saved_temp_path_in_bucket"],
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region,
            )

            # calls original function
            response = func(*args, **kwargs)
            # logger.info(response)
            # args[0].update_state(state=WorkerState.SUCCESS.name)
            alert_type = (SNSSubjectsAlert.SAVED_DATA.name,)
            error_output = ""
        except Exception as e:
            error_output = str(e).replace('"', " ").replace("'", " ")
            logger.error(f"Error :{error_output}")
            alert_type = SNSSubjectsAlert.SYSTEM_ERROR.name
            response = {
                "error": error_output,
            }
            logger.info("---------------")

        end_time = str(time.time())
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        pid = os.getpid()
        sns_message = {
            "file_name": curr_process_file,
            "column_name": curr_process_column,
            "task_id": task_id,
            "alert_type": alert_type,
            "start_time": start_time,
            "end_time": end_time,
            "hostname": hostname,
            "host_ip": host_ip,
            "pid": pid,
            "error": error_output,
        }
        # response = make_sns_response(
        #     alert_type=SNSSubjectsAlert.SYSTEM_ERROR.name,
        #     messages={
        #         "error": error_output,
        #         "file": curr_process_file,
        #         "column": curr_process_column,
        #         "alert_type": alert_type
        #     },
        #     user_id=user_id,
        # )
        # logger.error(f"Publish SNS Error{e}")
        # args[0].update_state(state=WorkerState.FAILED.name)

        try:
            # update_messages = response["Messages"]
            sns_message.update(response)
            # response["task_id"] = str(task_id)
            # response["alert_type"] = alert_type
            # response["start_time"] = start_time
            # response["end_time"] = end_time
            # response["hostname"] = hostname
            # response["host_ip"] = host_ip
            # response["pid"] = pid
            # response["file_name"] = curr_process_file
            # response["column_name"] = curr_process_column
        except Exception as e:
            error_output = str(e).replace('"', " ").replace("'", " ")
            logger.error(f"Error :{error_output}")
            alert_type = SNSSubjectsAlert.SYSTEM_ERROR.name
            sns_message["error"] = error_output
            sns_message["alert_type"] = alert_type

        # logger.info(update_messages)
        # subject = response["Subject"]
        # alert_type = subject["alert_type"]
        publish_message_sns(
            # message=json.dumps(update_messages),
            message=json.dumps(sns_message),
            subject=user_id,
            topic_arn=sns_topic,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        # logger.info(f" Send to SNS, message: {message_id}")

        # put_item_to_dynamodb(
        #     table_name=table_name,
        #     user_id=user_id,
        #     task_id=task_id,
        #     host_ip=host_ip,
        #     alert_type=alert_type,
        #     pid=pid,
        #     host_name=hostname,
        #     start_time=start_time,
        #     end_time=end_time,
        #     messages=json.dumps(update_messages),
        #     file_name=curr_process_file,
        #     column_name=curr_process_column,
        #     aws_access_key=aws_access_key,
        #     aws_secret_access_key=aws_secret_access_key,
        #     aws_region=aws_region,
        # )

    return wrapper


def put_item_to_dynamodb(
    table_name: str,
    user_id: str,
    task_id: str,
    host_ip: str,
    alert_type: str,
    pid: str,
    host_name: str,
    start_time: str,
    end_time: str,
    messages: str,
    file_name: str,
    column_name: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
):
    dynamodb_resource = boto3.resource(
        "dynamodb",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
    )
    table = dynamodb_resource.Table(table_name)
    response = table.put_item(
        Item={
            "user_id": user_id,
            "timestamp": str(time.time()),
            "host_name": host_name,
            "host_ip": host_ip,
            "task_id": task_id,
            "alert_type": alert_type,
            "pid": pid,
            "start_time": start_time,
            "end_time": end_time,
            "messages": messages,
            "file_name": file_name,
            "column_name": column_name,
        }
    )
    return response


# def make_sns_response(
#     alert_type: str = None, messages: dict = None, user_id: str = None
# ) -> dict:
#     subject = user_id
#     # messages["user_id"] = user_id

#     if alert_type is None or user_id is None:
#         subject["alert_type"] = SNSSubjectsAlert.SYSTEM_ERROR.name
#         messages["messages"] = "No alert_type or  user_id in sns message"
#         # subject = Alert.SYSTEM_ERROR.name
#         # messages = "No subject or user id in sns message"
#         raise Exception("Message Input Error")

#     if not isinstance(messages, dict):
#         raise Exception("messages is not a json object")

#     response = {"Subject": subject, "Messages": messages}
#     return response
