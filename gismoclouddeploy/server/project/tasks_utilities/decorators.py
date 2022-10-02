import json
import boto3

import functools
import time
import os
import socket
from .tasks_utils import (
    send_queue_message,
)

import logging
from models.SNSSubjectsAlert import SNSSubjectsAlert
from models.WorkerState import WorkerState

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
            aws_access_key = kwargs["aws_access_key"]
            aws_secret_access_key = kwargs["aws_secret_access_key"]
            aws_region = kwargs["aws_region"]
            sqs_url = kwargs["sqs_url"]
            user_id = kwargs["user_id"]
            po_server_name = kwargs["po_server_name"]

        except Exception as e:
            raise Exception(f"Decorator Input key errir:{e}")
        start_time = str(time.time())
        worker_state = WorkerState.RECEIVED.name
        response = dict()
        # print("Start-------->")
        try:

            response = func(*args, **kwargs)
            worker_state = WorkerState.SUCCESS.name
            # args[0].update_state(state=WorkerState.SUCCESS.name)
            alert_type = SNSSubjectsAlert.SAVED_DATA.name
            error_output = "None"
        except Exception as e:

            error_output = str(e).replace('"', " ").replace("'", " ")
            logger.error(f"Error :{error_output}")
            alert_type = SNSSubjectsAlert.SYSTEM_ERROR.name
            worker_state = WorkerState.FAILURE.name

        end_time = str(time.time())
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        pid = os.getpid()
        msg_body = {
            "po_server_name": po_server_name,
            "file_name": curr_process_file,
            "column_name": curr_process_column,
            "task_id": task_id,
            "alert_type": alert_type,
            "start_time": start_time,
            "end_time": end_time,
            "hostname": hostname,
            "host_ip": host_ip,
            "pid": pid,
            "data": response,
            "error": error_output,
        }
        MSG_ATTRIBUTES = {
            "user_id": {"DataType": "String", "StringValue": user_id},
        }
        # update worker state
        args[0].update_state(state=worker_state)

        # msg_body = {"data":response,"error": error_output}
        MSG_BODY = json.dumps(msg_body)
        # sqs_client = connect_aws_client(
        #     client_name="sqs",
        #     key_id=aws_access_key,
        #     secret=aws_secret_access_key,
        #     region=aws_region,
        # )
        sqs_client = boto3.client(
            "sqs",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
        )
        send_response = send_queue_message(
            queue_url=sqs_url,
            msg_attributes=MSG_ATTRIBUTES,
            msg_body=MSG_BODY,
            sqs_client=sqs_client,
        )
        print(f"---------> {curr_process_file}")

    return wrapper


# def connect_aws_client(client_name: str, key_id: str, secret: str, region: str):
#     try:
#         client = boto3.client(
#             client_name,
#             region_name=region,
#             aws_access_key_id=key_id,
#             aws_secret_access_key=secret,
#         )
#         return client

#     except Exception:
#         raise Exception("AWS Validation Error")
