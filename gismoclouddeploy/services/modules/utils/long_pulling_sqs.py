"""
This file is an old file contains long pulling sqs.

"""
from .WORKER_CONFIG import WORKER_CONFIG
from typing import List
from .check_aws import connect_aws_client
from .sqs import receive_queue_message, delete_queue_message
import time
import json
import logging
from server.models.SNSSubjectsAlert import SNSSubjectsAlert
import os
import pandas as pd
from os.path import exists

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


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
            print(f"{ worker_config.save_data_file_local} save_data: {save_data}")
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
            time.sleep(0.1)
            # wait_time -= int(1)
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
