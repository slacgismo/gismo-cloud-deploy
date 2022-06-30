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
from os.path import exists

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

from .dynamodb_utils import query_items_from_dynamodb_with_userid
from .command_utils import delete_files_from_bucket


def long_pulling_dynamodb(
    task_ids: List[str] = None,
    wait_time: int = 1,
    delay: int = None,
    sqs_url: str = None,
    worker_config: WORKER_CONFIG = None,
    is_docker: bool = False,
    acccepted_idle_time: int = 1,
    server_name: str = None,
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

    user_id = worker_config.user_id
    dynamodb_table = worker_config.dynamodb_tablename

    s3_client = connect_aws_client(
        "s3", key_id=aws_access_key, secret=aws_secret_access_key, region=aws_region
    )
    save_data_file = (
        worker_config.saved_path_local + "/" + worker_config.saved_data_target_filename
    )
    if exists(save_data_file):
        os.remove(save_data_file)
    delete_files_from_bucket(
        bucket_name=worker_config.saved_bucket,
        full_path=save_data_file,
        s3_client=s3_client,
    )
    save_logs_file = (
        worker_config.saved_path_local + "/" + worker_config.saved_logs_target_filename
    )
    if exists(save_logs_file):
        os.remove(save_logs_file)
    delete_files_from_bucket(
        bucket_name=worker_config.saved_bucket,
        full_path=save_logs_file,
        s3_client=s3_client,
    )

    save_error_file = (
        worker_config.saved_path_local + "/" + worker_config.saved_error_target_filename
    )
    if exists(save_error_file):
        os.remove(save_error_file)
    delete_files_from_bucket(
        bucket_name=worker_config.saved_bucket,
        full_path=save_error_file,
        s3_client=s3_client,
    )

    # clean previous files

    previous_messages_time = time.time()
    while wait_time > 0:
        # read items from dynamodb
        (
            remain_tasks_set,
            previous_messages_time,
        ) = query_items_from_dynamodb_with_userid(
            table_name=dynamodb_table,
            user_id=user_id,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            save_data_file=save_data_file,
            save_logs_file=save_logs_file,
            save_error_file=save_error_file,
            task_ids_set=task_ids_set,
            previous_messages_time=float(previous_messages_time),
        )
        len_remain_tasks = len(remain_tasks_set)
        task_completion = int(
            (total_task_length - len_remain_tasks) * 100 / (total_task_length)
        )
        idle_time = float(time.time()) - previous_messages_time
        logger.info(f"idle_time {idle_time}. Task completion: {task_completion} % ")

        # All task completed
        if len_remain_tasks == 0:
            logger.info("All task completed!!")
            return remain_tasks_set

        # Idle over time
        if idle_time > acccepted_idle_time:
            logger.info(f"===== No messages receive over time {idle_time} sec ====")
            logger.info(f"===== Number of unfinished tasks {len_remain_tasks} ====")
            return remain_tasks_set
            # for id in remain_tasks_set:
            #     logger.info(f"== Check id :{id} ==")
            # try:
            #     remain_tasks_set = check_tasks_status(
            #         is_docker=is_docker,
            #         server_name=server_name,
            #         task_ids_set=remain_tasks_set,
            #     )
            # except Exception as e:
            #     logger.error(f"Check task status failed :{e}")
            #     return remain_tasks_set
            # return remain_tasks_set

        time.sleep(delay)
        wait_time -= int(delay)

    return remain_tasks_set


def check_tasks_status(
    is_docker: bool = False,
    server_name: str = None,
    # task_id :str = None,
    task_ids_set: Set[str] = None,
) -> str:
    # unfinish_task_id_set = Set()
    unfinished_task_set = set()
    for task_id in task_ids_set:
        result = ""
        try:
            if is_docker:
                result = invoke_exec_docker_check_task_status(
                    server_name=server_name, task_id=str(task_id).strip("\n")
                )
            else:
                logger.info(f"Chcek--> {task_id} status")
                result = invoke_exec_k8s_check_task_status(
                    server_name=server_name, task_id=str(task_id).strip("\n")
                )
        except Exception as e:
            logger.error(f"Invokker check task status failed{e}")
            raise e
        logger.info(result)
        # conver json to
        res_json = {}
        dataform = str(result).strip("'<>() ").replace("'", '"').strip("\n")
        try:
            logger.info(f" ==== Id {task_id} Status: {res_json}====")
            res_json = json.loads(dataform)
            status = res_json["task_status"]

            if status != "SUCCESS":
                unfinished_task_set.add(task_id)
            else:
                logger.info(f"{task_id} success")
        except Exception as e:
            raise e
    logger.info(f"{len(unfinished_task_set)} of tasks unfinished.")
    return unfinished_task_set
