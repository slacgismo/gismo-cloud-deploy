import json
import boto3

import functools
import time
import os
import socket
from .tasks_utils import (
    publish_message_sns,
    check_and_download_solver,
)

import logging
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
            # args[0].update_state(state=WorkerState.SUCCESS.name)
            alert_type = SNSSubjectsAlert.SAVED_DATA.name
            error_output = ""
        except Exception as e:
            error_output = str(e).replace('"', " ").replace("'", " ")
            logger.error(f"Error :{error_output}")
            alert_type = SNSSubjectsAlert.SYSTEM_ERROR.name

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
            "data": "None",
            "error": error_output,
        }

        try:
            sns_message["data"] = json.dumps(response)
        except Exception as e:
            error_output = str(e).replace('"', " ").replace("'", " ")
            logger.error(f"Error :{error_output}")
            alert_type = SNSSubjectsAlert.SYSTEM_ERROR.name
            sns_message["alert_type"] = alert_type
            sns_message["error"] = error_output

        publish_message_sns(
            message=json.dumps(sns_message),
            subject=user_id,
            topic_arn=sns_topic,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )

    return wrapper
