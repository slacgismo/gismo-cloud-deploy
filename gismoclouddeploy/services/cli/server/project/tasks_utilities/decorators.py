from copy import copy
import json
import sys
import copy
import functools
import time
from .tasks_utils import (
    parse_messages_from_response,
    track_logs,
    publish_message_sns,
    parse_subject_from_response,
    check_and_download_solver,
)
from models.ActionState import ActionState
import logging
from models.WorkerState import WorkerState
from models.SNSSubjectsAlert import SNSSubjectsAlert
from decimal import Decimal

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
        except Exception as e:
            raise Exception(f"Decorator Input key errir:{e}")
        try:
            args[0].update_state(
                state=WorkerState.PROCESS.name, meta={"timestamp": str(time.time())}
            )

            # track start
            inspect_and_tracklog_decorator(
                function_name=func.__name__,
                action=ActionState.ACTION_START.name,
                messages="init function",
                task_id=task_id,
                process_file_name=curr_process_file,
                table_name=table_name,
                column_name=curr_process_column,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region,
            )

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

            args[0].update_state(
                state=WorkerState.SUCCESS.name, meta={"timestamp": str(time.time())}
            )
            # track end
            inspect_and_tracklog_decorator(
                function_name=func.__name__,
                action=ActionState.ACTION_STOP.name,
                messages=json.loads(json.dumps(response), parse_float=Decimal),
                task_id=task_id,
                process_file_name=curr_process_file,
                table_name=table_name,
                column_name=curr_process_column,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region,
            )

        except Exception as e:
            response = {
                "Subject": SNSSubjectsAlert.SYSTEM_ERROR.name,
                "Messages": {"error": f"{e}"},
            }
            logger.error(f"Publish SNS Error{e}")
            args[0].update_state(
                state=WorkerState.FAILED.name, meta={"timestamp": str(time.time())}
            )
        test_message = {"task_id": task_id}
        # raise Exception(f"Publish SNS Error:{e}")
        update_messages = response["Messages"]
        # update_messages['task_id'] = task_id
        # convert_json = json.loads(update_messages)
        # if not isinstance(update_messages, dict):
        #     update_messages = {"error": f"message is not dict {update_messages}"}

        # update_messages["task_id"] = str(task_id)
        message_id = publish_message_sns(
            # message=json.dumps(update_messages),
            message=json.dumps(update_messages),
            subject=parse_subject_from_response(response=response),
            topic_arn=sns_topic,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        # logger.info(f" Send to SNS, message: {message_id}")

    return wrapper


def inspect_and_tracklog_decorator(
    function_name,
    action,
    messages,
    task_id,
    process_file_name,
    table_name,
    column_name,
    aws_access_key,
    aws_secret_access_key,
    aws_region,
):
    """inspect function name, parameters"""

    try:
        track_logs(
            task_id=task_id,
            function_name=function_name,
            time=str(time.time()),
            action=action,
            message=messages,
            process_file_name=process_file_name,
            table_name=table_name,
            column_name=column_name,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
    except Exception as e:
        raise Exception(f"Tack log error:{e}")
