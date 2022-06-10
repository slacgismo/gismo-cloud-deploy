from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult

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


from .solardata import process_solardata_tools


@shared_task(bind=True)
@tracklog_decorator
def process_data_task(self, *arg, **kwargs):

    try:

        # task_id=self.request.id
        selected_algorithm = kwargs["selected_algorithm"]
        bucket_name = kwargs["bucket_name"]
        file_path_name = kwargs["file_path_name"]
        column_name = kwargs["column_name"]
        saved_bucket = kwargs["saved_bucket"]
        saved_file_path = kwargs["saved_file_path"]
        saved_filename = kwargs["saved_filename"]
        start_time = kwargs["start_time"]
        algorithms_params = kwargs["algorithms_params"]
        aws_access_key = kwargs["aws_access_key"]
        aws_secret_access_key = kwargs["aws_secret_access_key"]
        aws_region = kwargs["aws_region"]
        sns_topic = kwargs["sns_topic"]

    except Exception as e:
        # response['Subject'] = SNSSubjectsAlert.SYSTEM_ERROR.name
        # response['Message'] = f"Convert worker input keyword error:{e}"
        return tasks_utilities.tasks_utils.make_response(
            subject=SNSSubjectsAlert.SYSTEM_ERROR.name,
            messages=f"Convert worker input keyword error:{e}",
        )

    startime = str(time.time())
    self.update_state(state=WorkerState.PROGRESS.name, meta={"start": startime})
    task_id = self.request.id
    subject = task_id
    message = "init process_data_task"

    try:
        if selected_algorithm == "None":
            return "No selected algorithm"

        if selected_algorithm == "solar_data_tools":
            solar_params_obj = tasks_utilities.make_solardata_params_obj_from_json(
                algorithm_json=algorithms_params
            )
            process_solardata_tools(
                task_id=task_id,
                bucket_name=bucket_name,
                file_path_name=file_path_name,
                column_name=column_name,
                start_time=start_time,
                saved_bucket=saved_bucket,
                saved_file_path=saved_file_path,
                saved_filename=saved_filename,
                solarParams=solar_params_obj,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region,
            )
            message = "end of process data task"
    except Exception as e:
        # update task status as failed
        self.update_state(state=WorkerState.FAILED.name, meta={"start": startime})
        # send alert to sns and invoke cancel task fucntion
        return tasks_utilities.tasks_utils.make_response(
            subject=SNSSubjectsAlert.PROCESS_FILE_ERROR.name,
            messages=f"Process {file_path_name} column:{column_name} error: {e}",
        )
    # update task status as success
    self.update_state(state=WorkerState.SUCCESS.name, meta={"start": startime})

    return tasks_utilities.tasks_utils.make_response(
        subject=task_id,
        messages=f"Process {file_path_name} column:{column_name} success",
    )


@shared_task(bind=True)
@tracklog_decorator
def loop_tasks_status_task(self, *arg, **kwargs):
    startime = str(time.time())
    self.update_state(state=WorkerState.PROGRESS.name, meta={"start": startime})
    try:
        task_id = self.request.id
        delay = kwargs["delay"]
        interval_of_timeout = kwargs["interval_of_timeout"]
        bucket_name = kwargs["bucket_name"]
        task_ids = kwargs["task_ids"]
        bucket_name = kwargs["bucket_name"]
        source_folder = kwargs["source_folder"]
        target_folder = kwargs["target_folder"]
        target_filename = kwargs["target_filename"]
        aws_access_key = kwargs["aws_access_key"]
        aws_secret_access_key = kwargs["aws_secret_access_key"]
        aws_region = kwargs["aws_region"]
        sns_topic = kwargs["sns_topic"]

    except Exception as e:
        return tasks_utilities.tasks_utils.make_response(
            subject=SNSSubjectsAlert.SYSTEM_ERROR.name, messages=f"Loop task error:{e}"
        )

    interval_of_max_timeout = int(interval_of_timeout)
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
                            mesage_id = tasks_utilities.publish_message_sns(
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
        time.sleep(int(delay))

    logger.info(
        "------- start combine files, save logs , clean dynamodb items---------"
    )
    try:
        response = tasks_utilities.combine_files_to_file(
            bucket_name=bucket_name,
            source_folder=source_folder,
            target_folder=target_folder,
            target_filename=target_filename,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )

        # save_res = tasks_utilities.save_logs_from_dynamodb_to_s3(
        #     table_name=table_name,
        #     saved_bucket=bucket_name,
        #     saved_file_path=saved_log_file_path,
        #     saved_filename=saved_log_file_name,
        #     aws_access_key=aws_access_key,
        #     aws_secret_access_key=aws_secret_access_key,
        #     aws_region=aws_region,
        # )

        # remov_res = tasks_utilities.remove_all_items_from_dynamodb(
        #     table_name=table_name,
        #     aws_access_key=aws_access_key,
        #     aws_secret_access_key=aws_secret_access_key,
        #     aws_region=aws_region,
        # )

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


# @shared_task(bind=True)
# def process_data_task(
#     self,
#     selected_algorithm: str,
#     table_name: str,
#     bucket_name: str,
#     file_path_name: str,
#     column_name: str,
#     saved_bucket: str,
#     saved_file_path: str,
#     saved_filename: str,
#     start_time: str,
#     algorithms_params: str,
#     aws_access_key: str,
#     aws_secret_access_key: str,
#     aws_region: str,
#     sns_topic: str,
# ) -> str:

#     startime = str(time.time())
#     self.update_state(state=WorkerState.PROGRESS.name, meta={"start": startime})
#     task_id = self.request.id
#     subject = task_id
#     message = "init process_data_task"
#     try:
#         tasks_utilities.track_logs(
#             task_id=task_id,
#             function_name="process_data_task",
#             time=startime,
#             action=ActionState.ACTION_START.name,
#             message=message,
#             table_name=table_name,
#             process_file_name=file_path_name,
#             column_name=column_name,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )
#     except Exception as e:
#         return f"track logs error:{e}"

#     try:
#         if selected_algorithm == "None":
#             return "No selected algorithm"

#         if selected_algorithm == "solar_data_tools":
#             solar_params_obj = tasks_utilities.make_solardata_params_obj_from_json(
#                 algorithm_json=algorithms_params
#             )
#             process_solardata_tools(
#                 task_id=task_id,
#                 bucket_name=bucket_name,
#                 file_path_name=file_path_name,
#                 column_name=column_name,
#                 start_time=start_time,
#                 saved_bucket=saved_bucket,
#                 saved_file_path=saved_file_path,
#                 saved_filename=saved_filename,
#                 solarParams=solar_params_obj,
#                 aws_access_key=aws_access_key,
#                 aws_secret_access_key=aws_secret_access_key,
#                 aws_region=aws_region,
#             )
#             message = "end of process data task"
#     except Exception as e:
#         subject = SNSSubjectsAlert.PROCESS_FILE_ERROR.name
#         message = f"error:{e}"
#         logger.error(f"Error: {file_path_name} {column_name} :  {message} ")
#     try:
#         tasks_utilities.track_logs(
#             task_id=task_id,
#             function_name="process_data_task",
#             action=ActionState.ACTION_STOP.name,
#             time=str(time.time()),
#             message=message,
#             table_name=table_name,
#             process_file_name=file_path_name,
#             column_name=column_name,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )
#     except Exception as e:
#         return f"track logs error:{e}"
#     # send message
#     try:
#         mesage_id = tasks_utilities.publish_message_sns(
#             message=message,
#             subject=subject,
#             topic_arn=sns_topic,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )
#         logger.info(f" Send to SNS, message: {mesage_id}")
#     except Exception as e:
#         logger.error("Publish SNS Error")
#         return f"Publish SNS Error:{e}"

#     if subject == SNSSubjectsAlert.PROCESS_FILE_ERROR.name:
#         self.update_state(state=WorkerState.FAILED.name, meta={"start": startime})
#         return

#     self.update_state(state=WorkerState.SUCCESS.name, meta={"start": startime})


# @shared_task(bind=True)
# def loop_tasks_status_task(
#     self,
#     delay,
#     interval_of_timeout,
#     task_ids,
#     bucket_name,
#     source_folder,
#     target_folder,
#     target_filename,
#     table_name,
#     saved_log_file_path,
#     saved_log_file_name,
#     aws_access_key: str,
#     aws_secret_access_key: str,
#     aws_region: str,
#     sns_topic: str,
# ):
#     startime = str(time.time())
#     self.update_state(state=WorkerState.PROGRESS.name, meta={"start": startime})
#     interval_of_max_timeout = int(interval_of_timeout)
#     task_id = self.request.id
#     subject = task_id

#     message = "init loop_tasks_status_task"

#     tasks_utilities.track_logs(
#         task_id=task_id,
#         function_name="loop_tasks_status_task",
#         time=startime,
#         action=ActionState.ACTION_START.name,
#         message=message,
#         table_name=table_name,
#         process_file_name=None,
#         column_name=None,
#         aws_access_key=aws_access_key,
#         aws_secret_access_key=aws_secret_access_key,
#         aws_region=aws_region,
#     )

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
#                             mesage_id = tasks_utilities.publish_message_sns(
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

#     message = "end loop_tasks_status_task"
#     try:

#         tasks_utilities.track_logs(
#             task_id=self.request.id,
#             function_name="loop_tasks_status_task",
#             time=str(time.time()),
#             action=ActionState.ACTION_STOP.name,
#             message=message,
#             table_name=table_name,
#             process_file_name=None,
#             column_name=None,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )

#         response = tasks_utilities.combine_files_to_file(
#             bucket_name=bucket_name,
#             source_folder=source_folder,
#             target_folder=target_folder,
#             target_filename=target_filename,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )

#         save_res = tasks_utilities.save_logs_from_dynamodb_to_s3(
#             table_name=table_name,
#             saved_bucket=bucket_name,
#             saved_file_path=saved_log_file_path,
#             saved_filename=saved_log_file_name,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )

#         remov_res = tasks_utilities.remove_all_items_from_dynamodb(
#             table_name=table_name,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )

#         logger.info(
#             f"remov_res: {remov_res} save_res: {save_res}, response: {response}"
#         )
#         subject = SNSSubjectsAlert.All_TASKS_COMPLETED.name
#         message = SNSSubjectsAlert.All_TASKS_COMPLETED.name

#     except Exception as e:
#         subject = SNSSubjectsAlert.SYSTEM_ERROR.name
#         message = f"Loop task error:{e}"
#         logger.info(f"Error: {message} ")

#     try:
#         mesage_id = tasks_utilities.publish_message_sns(
#             message=message,
#             subject=subject,
#             topic_arn=sns_topic,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_region=aws_region,
#         )
#         logger.info(f" Send to SNS.----------> message: {mesage_id}")
#     except Exception as e:
#         raise e
