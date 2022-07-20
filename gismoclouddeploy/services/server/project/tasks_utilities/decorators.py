import json
import boto3

import functools
import time
import os
import socket
from .tasks_utils import (
    publish_message_sns,
    check_and_download_solver,
    send_queue_message,
    connect_aws_client
    
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
            solver = kwargs["solver"]
            aws_access_key = kwargs["aws_access_key"]
            aws_secret_access_key = kwargs["aws_secret_access_key"]
            aws_region = kwargs["aws_region"]
            sns_topic = kwargs["sns_topic"]
            sqs_url = kwargs["sqs_url"]
            user_id = kwargs["user_id"]

        except Exception as e:
            raise Exception(f"Decorator Input key errir:{e}")
        start_time = str(time.time())
        worker_state = WorkerState.RECEIVED.name
        response = dict()
        # print("Start-------->")
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
        # sns_message = {
        #     "file_name": curr_process_file,
        #     "column_name": curr_process_column,
        #     "task_id": task_id,
        #     "alert_type": alert_type,
        #     "start_time": start_time,
        #     "end_time": end_time,
        #     "hostname": hostname,
        #     "host_ip": host_ip,
        #     "pid": pid,
        #     "data": "None",
        #     "error": error_output,
        # }
        # try: 
        #     response_str = json.dumps(response)
        # except Exception:
        #     error_output = str(e).replace('"', " ").replace("'", " ")
        #     logger.error(f"Error :{error_output}")
        #     alert_type = SNSSubjectsAlert.SYSTEM_ERROR.name
        #     worker_state = WorkerState.FAILURE.name
        msg_body = {
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
                'user_id': {
                    'DataType': 'String',
                    'StringValue': user_id
                },
                # 'file_name': {
                #     'DataType': 'String',
                #     'StringValue': curr_process_file
                # },
                # 'column_name': {
                #     'DataType': 'String',
                #     'StringValue': curr_process_column
                # },
                # 'task_id': {
                #     'DataType': 'String',
                #     'StringValue': task_id
                # },
                # 'alert_type': {
                #     'DataType': 'String',
                #     'StringValue': alert_type
                # },
                # 'start_time': {
                #     'DataType': 'String',
                #     'StringValue': start_time,
                # },
                # 'end_time': {
                #     'DataType': 'String',
                #     'StringValue': end_time,
                # },
                # 'hostname': {
                #     'DataType': 'String',
                #     'StringValue': hostname,
                # },
                # 'host_ip': {
                #     'DataType': 'String',
                #     'StringValue': host_ip,
                # },
                # 'pid': {
                #     'DataType': 'String',
                #     'StringValue': str(pid),
                # }
            }
        # try:
        #     # MSG_ATTRIBUTES["data"] = json.dumps(response)
        #     MSG_ATTRIBUTES["data"] = 
        # except Exception as e:
            # error_output = str(e).replace('"', " ").replace("'", " ")
            # logger.error(f"Error :{error_output}")
            # alert_type = SNSSubjectsAlert.SYSTEM_ERROR.name
            # MSG_ATTRIBUTES["alert_type"] = alert_type
            # MSG_ATTRIBUTES["error"] = error_output
            # worker_state = WorkerState.FAILURE.name

        # publish_message_sns(
        #     message=json.dumps(sns_message),
        #     subject=user_id,
        #     topic_arn=sns_topic,
        #     aws_access_key=aws_access_key,
        #     aws_secret_access_key=aws_secret_access_key,
        #     aws_region=aws_region,
        # )
        
        # update worker state
        args[0].update_state(state=worker_state)

        # msg_body = {"data":response,"error": error_output}
        MSG_BODY = json.dumps(msg_body)
        sqs_client = connect_aws_client(
            client_name="sqs",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region
        )
        send_response = send_queue_message(
                    queue_url=sqs_url,
                    msg_attributes=MSG_ATTRIBUTES,
                    msg_body=MSG_BODY,
                    sqs_client=sqs_client

            )
        print(f"---------> {curr_process_file}")
        # print(send_response)

    return wrapper


