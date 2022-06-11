import sys

import functools
import time
from .tasks_utils import (
    track_logs,
    publish_message_sns,
    parse_messages_from_response,
    parse_subject_from_response,
)
from models.ActionState import ActionState
import logging

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
            process_file_name = kwargs["file_path_name"]
            column_name = kwargs["column_name"]
            aws_access_key = kwargs["aws_access_key"]
            aws_secret_access_key = kwargs["aws_secret_access_key"]
            aws_region = kwargs["aws_region"]

        except Exception as e:
            raise Exception(f"Decorator Input key errir:{e}")
        try:

            # track start
            inspect_and_tracklog_decorator(
                function_name=func.__name__,
                action=ActionState.ACTION_START.name,
                messages="init function",
                task_id=task_id,
                process_file_name=process_file_name,
                table_name=table_name,
                column_name=column_name,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region,
            )

            # calls original function
            response = func(*args, **kwargs)

            # track end
            inspect_and_tracklog_decorator(
                function_name=func.__name__,
                action=ActionState.ACTION_STOP.name,
                messages=response,
                task_id=task_id,
                process_file_name=process_file_name,
                table_name=table_name,
                column_name=column_name,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region,
            )

            # send message

            mesage_id = publish_message_sns(
                message=parse_messages_from_response(response=response),
                subject=parse_subject_from_response(response=response),
                topic_arn=kwargs["sns_topic"],
                aws_access_key=kwargs["aws_access_key"],
                aws_secret_access_key=kwargs["aws_secret_access_key"],
                aws_region=kwargs["aws_region"],
            )
            logger.info(f" Send to SNS, message: {mesage_id}")
        except Exception as e:
            logger.error("Publish SNS Error")
            raise Exception(f"Publish SNS Error:{e}")

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
