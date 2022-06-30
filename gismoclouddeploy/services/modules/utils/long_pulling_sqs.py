"""
This file is an old file contains long pulling sqs.

"""
from .WORKER_CONFIG import WORKER_CONFIG
from typing import List, Set
from .check_aws import connect_aws_client
from .sqs import receive_queue_message, delete_queue_message
import time
import json
import logging
from server.models.SNSSubjectsAlert import SNSSubjectsAlert
from .invoke_function import (
    invoke_exec_docker_check_task_status,
    invoke_exec_k8s_check_task_status,
)
import os
import pandas as pd
from os.path import exists

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

# from .dynamodb_utils import query_items_from_dynamodb_with_userid
# from .command_utils import delete_files_from_bucket


# def long_pulling_dynamodb(
#     task_ids: List[str] = None,
#     wait_time: int = 1,
#     delay: int = None,
#     sqs_url: str = None,
#     worker_config: WORKER_CONFIG = None,
#     is_docker: bool = False,
#     acccepted_idle_time: int = 1,
#     server_name: str = None,
#     aws_access_key: str = None,
#     aws_secret_access_key: str = None,
#     aws_region: str = None,
# ) -> None:

#     task_ids_set = set(task_ids)
#     total_task_length = len(task_ids_set)
#     sqs_client = connect_aws_client(
#         client_name="sqs",
#         key_id=aws_access_key,
#         secret=aws_secret_access_key,
#         region=aws_region,
#     )


#     user_id = worker_config.user_id
#     dynamodb_table = worker_config.dynamodb_tablename

#     s3_client = connect_aws_client(
#         "s3",
#         key_id= aws_access_key,
#         secret= aws_secret_access_key,
#         region=aws_region
#     )
#     save_data_file = (
#         worker_config.saved_path + "/" + worker_config.saved_data_target_filename
#     )
#     if exists(save_data_file):
#         os.remove(save_data_file)
#     delete_files_from_bucket(
#         bucket_name=worker_config.saved_bucket,
#         full_path=save_data_file,
#         s3_client= s3_client
#     )
#     save_logs_file = (
#         worker_config.saved_path + "/" + worker_config.saved_logs_target_filename
#     )
#     if exists(save_logs_file):
#         os.remove(save_logs_file)
#     delete_files_from_bucket(
#         bucket_name=worker_config.saved_bucket,
#         full_path=save_logs_file,
#         s3_client= s3_client
#     )

#     save_error_file = (
#         worker_config.saved_path + "/" + worker_config.saved_error_target_filename
#     )
#     if exists(save_error_file):
#         os.remove(save_error_file)
#     delete_files_from_bucket(
#         bucket_name=worker_config.saved_bucket,
#         full_path=save_error_file,
#         s3_client= s3_client
#     )

#     # clean previous files

#     previous_messages_time = time.time()
#     while wait_time > 0:
#         # read items from dynamodb
#         remain_tasks_set,previous_messages_time = query_items_from_dynamodb_with_userid(
#             table_name= dynamodb_table,
#             user_id=user_id,
#             aws_access_key=aws_access_key,
#             aws_secret_access_key = aws_secret_access_key,
#             aws_region = aws_region,
#             save_data_file = save_data_file,
#             save_logs_file = save_logs_file,
#             save_error_file = save_error_file,
#             task_ids_set=task_ids_set,
#             previous_messages_time = float(previous_messages_time)

#         )
#         remain_tasks = len(remain_tasks_set)

#         idle_time = float(time.time()) - previous_messages_time
#         logger.info(f"idle_time {idle_time}. ")
#         if len(remain_tasks_set) == 0 :
#             logger.info("All task completed!!")
#             return remain_tasks
#         if idle_time > acccepted_idle_time:
#             logger.info(f"===== No messages receive over time {idle_time} sec ====")
#             logger.info(f"===== Number of unfinished tasks {len(remain_tasks_set)} ====")
#             for id in task_ids_set:
#                 logger.info(f"== Check id :{id} ==")
#             try:
#                 remain_tasks = check_tasks_status(
#                     is_docker=is_docker,
#                     server_name=server_name,
#                     task_ids_set=task_ids_set,
#                 )
#             except Exception as e:
#                 logger.error(f"Check task status failed :{e}")
#                 return remain_tasks
#             return remain_tasks
#         time.sleep(delay)
#         wait_time -= int(delay)
#     # save local data to s3

#     return remain_tasks


def remove_prevous_results_files(
    save_data_file_local: str = None,
    save_logs_file_local: str = None,
    save_error_file_local: str = None,
) -> None:

    if exists(save_data_file_local):
        os.remove(save_data_file_local)

    if exists(save_logs_file_local):
        os.remove(save_logs_file_local)

    if exists(save_error_file_local):
        os.remove(save_error_file_local)


def long_pulling_sqs(
    worker_config: WORKER_CONFIG = None,
    task_ids: List[str] = None,
    wait_time: int = 1,
    delay: int = None,
    sqs_url: str = None,
    acccepted_idle_time: int = 1,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:

    task_ids_set = set(task_ids)
    total_task_length = len(task_ids_set)
    sqs_client = connect_aws_client(
        client_name="sqs",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    previous_messages_time = time.time()
    numb_tasks_completed = 0
    task_completion = 0

    remove_prevous_results_files(
        save_data_file_local=worker_config.save_data_file_local,
        save_logs_file_local=worker_config.save_logs_file_local,
        save_error_file_local=worker_config.save_error_file_local,
    )

    while wait_time > 0:
        messages = receive_queue_message(
            sqs_url, sqs_client, MaxNumberOfMessages=10, wait_time=delay
        )
        save_data = []
        logs_data = []
        error_data = []
        if "Messages" in messages:
            for msg in messages["Messages"]:
                msg_body = json.loads(msg["Body"])

                receipt_handle = msg["ReceiptHandle"]
                subject = (
                    msg_body["Subject"].strip("'<>() ").replace("'", '"').strip("\n")
                )
                message_text = (
                    msg_body["Message"].strip("'<>() ").replace("'", '"').strip("\n")
                )
                logger.info(f"subject: {subject}")
                logger.info(f"message_text: {message_text}")
                # try:
                #     # subject_info = json.loads(subject)
                #     # sns_user_id = subject_info["user_id"]
                # except Exception as e:
                #     logger.error(f"Cannot parse {subject_info} from SQS {e}")
                #     raise e
                if subject != worker_config.user_id:
                    # not this user's sqs message. do touch
                    continue
                # parse Message
                previous_messages_time = time.time()

                try:
                    message_json = json.loads(message_text)
                    alert_type = message_json["alert_type"]
                    task_id = message_json["task_id"]

                except Exception as e:
                    logger.error(f"Cannot parse {message_json} from SQS {e}")
                    logger.error(
                        f"Cannot parse task id. But we consider this task completed. Delete this message"
                    )
                    numb_tasks_completed += 1
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    continue

                if task_id in task_ids_set:
                    numb_tasks_completed += 1
                    task_ids_set.remove(task_id)
                    task_completion = int(
                        numb_tasks_completed * 100 / total_task_length
                    )
                    logger.info(
                        f"Complete task: {numb_tasks_completed} totl:{total_task_length} task_completion: {task_completion} %"
                    )
                    # Save loags
                    logs_data.append(message_json)
                    # Save errors
                    if alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name:
                        error_data.append(message_json)
                    # Save data
                    if alert_type == SNSSubjectsAlert.SAVED_DATA.name:
                        save_data.append(message_json)
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)

        if len(save_data) > 0:
            save_data_df = pd.json_normalize(save_data)
            save_data_df.to_csv(
                worker_config.save_data_file_local,
                mode="a",
                header=not os.path.exists(worker_config.save_data_file_local),
            )
        if len(error_data) > 0:
            save_error_df = pd.json_normalize(error_data)
            save_error_df.to_csv(
                worker_config.save_error_file_local,
                mode="a",
                header=not os.path.exists(worker_config.save_error_file_local),
            )
        if len(logs_data) > 0:
            save_logs_df = pd.json_normalize(logs_data)
            save_logs_df.to_csv(
                worker_config.save_logs_file_local,
                mode="a",
                header=not os.path.exists(worker_config.save_logs_file_local),
            )
        if len(logs_data) > 0 and numb_tasks_completed < total_task_length:
            time.sleep(1)
            wait_time -= int(1)
            logger.info("Retrieve SQS messages again...")
            # don't wait ,get messages again
            continue

        logger.info(
            f" Waiting .: {wait_time - delay} \
            Time: {time.ctime(time.time())} "
        )
        if numb_tasks_completed == total_task_length:
            logger.info("===== All task completed ====")
            if len(task_ids_set) > 0:
                for id in task_ids_set:
                    logger.info(f"Cannot parse message from {id}!!. Somehing wrong!! ")
            return task_ids_set
        idle_time = time.time() - previous_messages_time
        if idle_time >= acccepted_idle_time:
            logger.info(f"===== No messages receive over time {idle_time} sec ====")
            logger.info(f"===== Number of unfinished tasks {len(task_ids_set)} ====")
            return task_ids_set
        time.sleep(delay)
        wait_time -= int(delay)
    return task_ids_set


# def long_pulling_sqs(
#     worker_config: WORKER_CONFIG = None,
#     task_ids: List[str] = None,
#     wait_time: int = 1,
#     delay: int = None,
#     sqs_url: str = None,
#     acccepted_idle_time: int = 1,
#     aws_access_key: str = None,
#     aws_secret_access_key: str = None,
#     aws_region: str = None,
# ) -> None:

#     task_ids_set = set(task_ids)
#     total_task_length = len(task_ids_set)
#     sqs_client = connect_aws_client(
#         client_name="sqs",
#         key_id=aws_access_key,
#         secret=aws_secret_access_key,
#         region=aws_region,
#     )
#     previous_messages_time = time.time()
#     numb_tasks_completed = 0
#     task_completion = 0

#     remove_prevous_results_files(
#         save_data_file_local=worker_config.save_data_file_local,
#         save_logs_file_local=worker_config.save_logs_file_local,
#         save_error_file_local=worker_config.save_error_file_local,
#     )


#     while wait_time > 0:
#         messages = receive_queue_message(
#             sqs_url, sqs_client, MaxNumberOfMessages=10, wait_time=delay
#         )
#         save_data = []
#         logs_data = []
#         error_data =[]
#         if "Messages" in messages:
#             for msg in messages["Messages"]:
#                 msg_body = json.loads(msg["Body"])

#                 receipt_handle = msg["ReceiptHandle"]
#                 subject = (
#                     msg_body["Subject"].strip("'<>() ").replace("'", '"').strip("\n")
#                 )
#                 message_text = (
#                     msg_body["Message"].strip("'<>() ").replace("'", '"').strip("\n")
#                 )
#                 try:
#                     subject_info = json.loads(subject)
#                     sns_user_id = subject_info["user_id"]
#                 except Exception as e:
#                     logger.error(f"Cannot parse {subject_info} from SQS {e}")
#                     raise e
#                 if sns_user_id != worker_config.user_id:
#                     continue
#                 # parse Message
#                 try:
#                     message_json = json.loads(message_text)
#                     alert_type = subject_info["alert_type"]
#                     task_id = message_json["task_id"]

#                 except Exception as e:
#                     logger.error(f"Cannot parse {message_json} from SQS {e}")
#                     logger.error(
#                         f"Cannot parse task id. But we consider this task completed"
#                     )
#                     numb_tasks_completed += 1
#                     continue

#                 if alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name :
#                     error_data.append(message_json)

#                 if alert_type == SNSSubjectsAlert.SAVED_DATA.name :
#                     save_data.append(message_json)


#                 if task_id in task_ids_set:
#                     task_ids_set.remove(task_id)
#                     numb_tasks_completed += 1
#                     task_completion = int(
#                         numb_tasks_completed * 100 / total_task_length
#                     )
#                     logger.info(message_json)
#                     logger.info(
#                         f"Complete task: {numb_tasks_completed} totl:{total_task_length} task_completion: {task_completion} %"
#                     )


#                     previous_messages_time = time.time()
#                     delete_queue_message(sqs_url, receipt_handle, sqs_client)
#                 else:
#                     continue

#                 delete_queue_message(sqs_url, receipt_handle, sqs_client)
#         logger.info(
#             f" Waiting .: {wait_time - delay} \
#             Time: {time.ctime(time.time())} "
#         )
#         if numb_tasks_completed == total_task_length:
#             logger.info("===== All task completed ====")
#             if len(task_ids_set) > 0:
#                 for id in task_ids_set:
#                     logger.info(f"Cannot parse message from {id}!!. Somehing wrong!! ")
#             return
#         idle_time = time.time() - previous_messages_time
#         if idle_time >= acccepted_idle_time:
#             logger.info(f"===== No messages receive over time {idle_time} sec ====")
#             logger.info(f"===== Number of unfinished tasks {len(task_ids_set)} ====")
#             return task_ids_set
#         time.sleep(delay)
#         wait_time -= int(delay)
#     return task_ids_set


# def check_tasks_status(
#     is_docker: bool = False,
#     server_name: str = None,
#     # task_id :str = None,
#     task_ids_set: Set[str] = None,
# ) -> str:
#     # unfinish_task_id_set = Set()
#     unfinished_task_set = set()
#     for task_id in task_ids_set:
#         result = ""
#         try:
#             if is_docker:
#                 result = invoke_exec_docker_check_task_status(
#                     server_name=server_name, task_id=str(task_id).strip("\n")
#                 )
#             else:
#                 logger.info(f"Chcek--> {task_id} status")
#                 result = invoke_exec_k8s_check_task_status(
#                     server_name=server_name, task_id=str(task_id).strip("\n")
#                 )
#         except Exception as e:
#             logger.error(f"Invokker check task status failed{e}")
#             raise e
#         logger.info(result)
#         # conver json to
#         res_json = {}
#         dataform = str(result).strip("'<>() ").replace("'", '"').strip("\n")
#         try:
#             logger.info(f" ==== Id {task_id} Status: {res_json}====")
#             res_json = json.loads(dataform)
#             status = res_json["task_status"]

#             if status != "SUCCESS":
#                 unfinished_task_set.add(task_id)
#             else:
#                 logger.info(f"{task_id} success")
#         except Exception as e:
#             raise e
#     logger.info(f"{len(unfinished_task_set)} of tasks unfinished.")
#     return unfinished_task_set
