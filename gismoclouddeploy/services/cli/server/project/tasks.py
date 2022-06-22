from cmath import log
import re
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
from utils.aws_utils import connect_aws_client

from models.SNSSubjectsAlert import SNSSubjectsAlert
import time

from project import tasks_utilities
from project.tasks_utilities.decorators import tracklog_decorator

from models.WorkerState import WorkerState
import json
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)
from .tasks_utilities.decorators import make_sns_response

import json

from .entrypoint import entrypoint


@shared_task(bind=True)
def pong_worker(
    *args,
    **kwargs,
):
    return "ok"


@shared_task(bind=True)
@tracklog_decorator
def process_data_task(
    *args,
    **kwargs,
):
    try:
        data_bucket = kwargs["data_bucket"]
        curr_process_file = kwargs["curr_process_file"]
        curr_process_column = kwargs["curr_process_column"]
        aws_access_key = kwargs["aws_access_key"]
        aws_secret_access_key = kwargs["aws_secret_access_key"]
        aws_region = kwargs["aws_region"]
        solver_name = kwargs["solver"]["solver_name"]
        solver_file = (
            kwargs["solver"]["solver_lic_target_path"]
            + "/"
            + kwargs["solver"]["solver_lic_file_name"]
        )
        user_id = kwargs["user_id"]
    except Exception as e:
        raise Exception(f"Input key error:{e}")

    response = entrypoint(
        user_id=user_id,
        data_bucket=data_bucket,
        curr_process_file=curr_process_file,
        curr_process_column=curr_process_column,
        solver_name=solver_name,
        solver_file=solver_file,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
    )
    return response


@shared_task(bind=True)
@tracklog_decorator
def loop_tasks_status_task(
    self,
    task_ids,
    **kwargs,
):
    # for id in task_ids:
    #     print(id)

    timestamp = str(time.time())

    try:
        task_id = self.request.id
        aws_access_key = str(kwargs["aws_access_key"])
        aws_secret_access_key = str(kwargs["aws_secret_access_key"])
        aws_region = str(kwargs["aws_region"])
        sns_topic = kwargs["sns_topic"]
        interval_of_max_timeout = kwargs["interval_of_exit_check_status"]
        interval_of_check_task_status = kwargs["interval_of_check_task_status"]
        user_id = kwargs["user_id"]

    except Exception as e:
        return tasks_utilities.tasks_utils.make_response(
            subject=SNSSubjectsAlert.SYSTEM_ERROR.name, messages=f"Loop task error:{e}"
        )

    task_id = self.request.id
    subject = task_id
    while len(task_ids) > 0:
        for id in task_ids[:]:
            res = AsyncResult(str(id))
            status = str(res.status)

            if res.info is None:
                logger.info(
                    f"=================={status}!!! This task has no info.It dose not start {res} "
                )
            else:
                try:
                    # logger.info(f"========== has info === {res}")
                    star_time = res.info["timestamp"]
                    curr_time = time.time()
                    duration = int(curr_time - float(star_time))
                    # if the duration of task is over timeout stop
                    if duration >= int(interval_of_max_timeout):
                        # remove id to avoid duplicated sns message
                        task_ids.remove(id)
                        try:
                            data = {}
                            #
                            subject = {
                                "alert_type": SNSSubjectsAlert.TIMEOUT.name,
                                "user_id": user_id,
                            }
                            message = {"user_id": user_id, "task_id": task_id}
                            tasks_utilities.publish_message_sns(
                                message=json.dumps(message),
                                subject=json.dumps(subject),
                                topic_arn=sns_topic,
                                aws_access_key=aws_access_key,
                                aws_secret_access_key=aws_secret_access_key,
                                aws_region=aws_region,
                            )
                        except Exception as e:
                            logger.error(f"SYSTEM error :{e}")
                            raise e
                        logger.warning(
                            f"====== Timeout {id} durtaion: {duration} send sns timeout alert ====== "
                        )

                except Exception as e:
                    logger.info(f"no start key in info: {e}")
            # if tasks success failed or revoked
            if (
                status == WorkerState.SUCCESS.name
                or status == WorkerState.FAILED.name
                or status == WorkerState.REVOKED.name
            ):
                logger.info(
                    f"completed schedulers: id: {res.task_id} \n task status: {res.status} "
                )
                # delete id from task_ids
                task_ids.remove(id)
        time.sleep(int(interval_of_check_task_status))

    logger.info("------- All tasks are done !!! ---------")

    # subject = SNSSubjectsAlert.All_TASKS_COMPLETED.name
    # message = {"task_id": task_id, "message": "loog tasks completes"}

    # return tasks_utilities.tasks_utils.make_response(subject=subject, messages=message)
    return make_sns_response(
        alert_type=SNSSubjectsAlert.All_TASKS_COMPLETED.name,
        messages={"task_id": task_id},
        user_id=user_id,
    )
