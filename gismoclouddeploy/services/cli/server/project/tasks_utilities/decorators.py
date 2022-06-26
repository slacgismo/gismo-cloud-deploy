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
            user_id = kwargs["user_id"]
        except Exception as e:
            raise Exception(f"Decorator Input key errir:{e}")
        try:
            # args[0].update_state(
            #     state=WorkerState.PROCESS.name, meta={"timestamp": str(time.time())}
            # )
            start_time = str(time.time())
            # track start
            inspect_and_tracklog_decorator(
                function_name=func.__name__,
                action=ActionState.ACTION_START.name,
                user_id=user_id,
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

            # args[0].update_state(
            #     state=WorkerState.SUCCESS.name, meta={"timestamp": str(time.time())}
            # )
            args[0].update_state(state=WorkerState.SUCCESS.name)
            # track end

        except Exception as e:
            response = make_sns_response(
                alert_type=SNSSubjectsAlert.SYSTEM_ERROR.name,
                messages={"error": f"{e}"},
                user_id=user_id,
            )
            logger.error(f"Publish SNS Error{e}")
            args[0].update_state(state=WorkerState.FAILED.name)

        inspect_and_tracklog_decorator(
            function_name=func.__name__,
            action=ActionState.ACTION_STOP.name,
            user_id=user_id,
            messages=json.loads(json.dumps(response), parse_float=Decimal),
            task_id=task_id,
            process_file_name=curr_process_file,
            table_name=table_name,
            column_name=curr_process_column,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        # subject_str = parse_subject_from_response(response=response,task_id=task_id)
        end_time = str(time.time())
        update_messages = response["Messages"]
        update_messages["task_id"] = str(task_id)
        update_messages["start_time"] = start_time
        update_messages["end_time"] = end_time
        logger.info(update_messages)
        subject = response["Subject"]

        publish_message_sns(
            # message=json.dumps(update_messages),
            message=json.dumps(update_messages),
            subject=json.dumps(subject),
            topic_arn=sns_topic,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        # logger.info(f" Send to SNS, message: {message_id}")

    return wrapper


def inspect_and_tracklog_decorator(
    function_name,
    user_id,
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
            user_id=user_id,
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


def make_sns_response(
    alert_type: str = None, messages: dict = None, user_id: str = None
) -> dict:
    subject = {"alert_type": alert_type, "user_id": user_id}
    messages["user_id"] = user_id

    if alert_type is None or user_id is None:
        subject["alert_type"] = SNSSubjectsAlert.SYSTEM_ERROR.name
        messages["messages"] = "No alert_type or  user_id in sns message"
        # subject = Alert.SYSTEM_ERROR.name
        # messages = "No subject or user id in sns message"
        raise Exception("Message Input Error")

    if not isinstance(messages, dict):
        raise Exception("messages is not a json object")

    response = {"Subject": subject, "Messages": messages}
    return response
