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


from .solardata.start import entrypoint

import json
from types import SimpleNamespace


@shared_task(bind=True)
@tracklog_decorator
def process_data_task(
    self,
    **kwargs,
):

    return tasks_utilities.tasks_utils.make_response(subject="test", messages="test")


@shared_task(bind=True)
@tracklog_decorator
def loop_tasks_status_task(
    self,
    task_ids,
    **kwargs,
):
    print("--------------?>>>")
    logger.info("loop task status")
    for id in task_ids:
        print(id)

    startime = str(time.time())
    self.update_state(state=WorkerState.PROGRESS.name, meta={"start": startime})

    try:
        task_id = self.request.id
        aws_access_key = str(kwargs["aws_access_key"])
        aws_secret_access_key = str(kwargs["aws_secret_access_key"])
        aws_region = str(kwargs["aws_region"])
        sns_topic = kwargs["sns_topic"]
        interval_of_max_timeout = kwargs["interval_of_exit_check_status"]
        saved_bucket = kwargs["saved_bucket"]
        saved_tmp_path = kwargs["saved_tmp_path"]
        saved_target_path = kwargs["saved_target_path"]
        saved_target_filename = kwargs["usaved_target_filename"]
        interval_of_check_task_status = kwargs["interval_of_check_task_status"]

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
                logger.info("no info")
            else:
                try:
                    star_time = res.info["start"]
                    curr_time = time.time()
                    duration = int(curr_time - float(star_time))
                    # if the duration of task is over timeout stop
                    if duration >= int(interval_of_max_timeout):
                        # remove id to avoid duplicated sns message
                        task_ids.remove(id)
                        try:
                            data = {}
                            data["task_id"] = f"{id}"
                            tasks_utilities.publish_message_sns(
                                message=json.dumps(data),
                                subject=SNSSubjectsAlert.TIMEOUT.name,
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

    logger.info(
        "------- start combine files, save logs , clean dynamodb items---------"
    )
    try:
        response = tasks_utilities.combine_files_to_file(
            bucket_name=saved_bucket,
            source_folder=saved_tmp_path,
            target_folder=saved_target_path,
            target_filename=saved_target_filename,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )

        logger.info(f"response: {response}")
        subject = SNSSubjectsAlert.All_TASKS_COMPLETED.name
        message = SNSSubjectsAlert.All_TASKS_COMPLETED.name

    except Exception as e:
        subject = SNSSubjectsAlert.SYSTEM_ERROR.name
        message = f"Loop task error:{e}"

        return tasks_utilities.tasks_utils.make_response(
            subject=subject, messages=message
        )

    return tasks_utilities.tasks_utils.make_response(subject=subject, messages=message)

    # logger.info(
    #     "------- start combine files, save logs , clean dynamodb items---------"
    # )
    # try:
    #     response = tasks_utilities.combine_files_to_file(
    #         bucket_name=bucket_name,
    #         source_folder=source_folder,
    #         target_folder=target_folder,
    #         target_filename=target_filename,
    #         aws_access_key=aws_access_key,
    #         aws_secret_access_key=aws_secret_access_key,
    #         aws_region=aws_region,
    #     )

    #     logger.info(f"response: {response}")
    #     subject = SNSSubjectsAlert.All_TASKS_COMPLETED.name
    #     message = SNSSubjectsAlert.All_TASKS_COMPLETED.name

    # except Exception as e:
    #     subject = SNSSubjectsAlert.SYSTEM_ERROR.name
    #     message = f"Loop task error:{e}"

    # return tasks_utilities.tasks_utils.make_response(
    #     subject=subject, messages=message
    # )

    # return tasks_utilities.tasks_utils.make_response(subject=subject, messages=message)

    # Parse JSON into an object with attributes corresponding to dict keys.

    # startime = str(time.time())
    # self.update_state(state=WorkerState.PROGRESS.name, meta={"start": startime})
    # task_id = self.request.id
    # subject = task_id
    # message = "init process_data_task"

    # try:
    #     file_path_name = kwargs["file_path_name"]
    #     column_name = kwargs["column_name"]
    #     aws_access_key = str(kwargs["aws_access_key"])
    #     aws_secret_access_key = str(kwargs["aws_secret_access_key"])
    #     aws_region = str(kwargs["aws_region"])
    #     sns_topic = kwargs["sns_topic"]

    # except Exception as e:
    #     return tasks_utilities.tasks_utils.make_response(
    #         subject=SNSSubjectsAlert.SYSTEM_ERROR.name,
    #         messages=f"Convert worker input keyword error:{e}",
    #     )
    # try:
    #     logger.info("process -------> ")
    #     logger.info(kwargs)
    #     logger.info("process -------> ")
    #         # entrypoint(
    #         #     task_id=task_id,
    #         #     bucket_name=bucket_name,
    #         #     file_path_name=file_path_name,
    #         #     column_name=column_name,
    #         #     start_time=start_time,
    #         #     saved_bucket=saved_bucket,
    #         #     saved_file_path=saved_file_path,
    #         #     saved_filename=saved_filename,
    #         #     aws_access_key=aws_access_key,
    #         #     aws_secret_access_key=aws_secret_access_key,
    #         #     aws_region=aws_region,
    #         # )
    #         # message = (f"Process {file_path_name} column:{column_name} success",)
    # except Exception as e:
    #     # update task status as failed
    #     self.update_state(state=WorkerState.FAILED.name, meta={"start": startime})
    #     # send alert to sns and invoke cancel task fucntion
    #     return tasks_utilities.tasks_utils.make_response(
    #         subject=SNSSubjectsAlert.PROCESS_FILE_ERROR.name,
    #         messages=f"Process {file_path_name} column:{column_name} error: {e}",
    #     )
    # # update task status as success
    # self.update_state(state=WorkerState.SUCCESS.name, meta={"start": startime})

    # return tasks_utilities.tasks_utils.make_response(
    #     subject=task_id,
    #     messages=message,
    # )


# @shared_task(bind=True)
# @tracklog_decorator
# def loop_tasks_status_task(
#     self,
#     delay,
#     interval_of_timeout,
#     task_ids,
#     bucket_name,
#     source_folder,
#     target_folder,
#     target_filename,
#     **kwargs,
# ):
#     startime = str(time.time())
#     self.update_state(state=WorkerState.PROGRESS.name, meta={"start": startime})
#     try:
#         task_id = self.request.id
#         aws_access_key = str(kwargs["aws_access_key"])
#         aws_secret_access_key = str(kwargs["aws_secret_access_key"])
#         aws_region = str(kwargs["aws_region"])
#         sns_topic = kwargs["sns_topic"]

#     except Exception as e:
#         return tasks_utilities.tasks_utils.make_response(
#             subject=SNSSubjectsAlert.SYSTEM_ERROR.name, messages=f"Loop task error:{e}"
#         )

#     interval_of_max_timeout = int(interval_of_timeout)
#     task_id = self.request.id
#     subject = task_id
#     while len(task_ids) > 0:
#         for id in task_ids[:]:
#             res = AsyncResult(str(id))
#             status = str(res.status)
#             if res.info is None:
#                 logger.info("no info")
#             else:
#                 try:
#                     star_time = res.info["start"]
#                     curr_time = time.time()
#                     duration = int(curr_time - float(star_time))
#                     # if the duration of task is over timeout stop
#                     if duration >= int(interval_of_max_timeout):
#                         # remove id to avoid duplicated sns message
#                         task_ids.remove(id)
#                         try:
#                             data = {}
#                             data["task_id"] = f"{id}"
#                             tasks_utilities.publish_message_sns(
#                                 message=json.dumps(data),
#                                 subject=SNSSubjectsAlert.TIMEOUT.name,
#                                 topic_arn=sns_topic,
#                                 aws_access_key=aws_access_key,
#                                 aws_secret_access_key=aws_secret_access_key,
#                                 aws_region=aws_region,
#                             )
#                         except Exception as e:
#                             logger.error(f"SYSTEM error :{e}")
#                             raise e
#                         logger.warning(
#                             f"====== Timeout {id} durtaion: {duration} send sns timeout alert ====== "
#                         )

#                 except Exception as e:
#                     logger.info(f"no start key in info: {e}")
#             # if tasks success failed or revoked
#             if (
#                 status == WorkerState.SUCCESS.name
#                 or status == WorkerState.FAILED.name
#                 or status == WorkerState.REVOKED.name
#             ):
#                 logger.info(
#                     f"completed schedulers: id: {res.task_id} \n task status: {res.status} "
#                 )
#                 # delete id from task_ids
#                 task_ids.remove(id)
#         time.sleep(int(delay))

#     logger.info(
#         "------- start combine files, save logs , clean dynamodb items---------"
#     )
#     try:
#         response = tasks_utilities.combine_files_to_file(
#             bucket_name=bucket_name,
#             source_folder=source_folder,
#             target_folder=target_folder,
#             target_filename=target_filename,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )

#         logger.info(f"response: {response}")
#         subject = SNSSubjectsAlert.All_TASKS_COMPLETED.name
#         message = SNSSubjectsAlert.All_TASKS_COMPLETED.name

#     except Exception as e:
#         subject = SNSSubjectsAlert.SYSTEM_ERROR.name
#         message = f"Loop task error:{e}"

#         return tasks_utilities.tasks_utils.make_response(
#             subject=subject, messages=message
#         )

#     return tasks_utilities.tasks_utils.make_response(subject=subject, messages=message)
