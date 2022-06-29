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

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def long_pulling_sqs(
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
    previous_messages_time = time.time()
    numb_tasks_completed = 0
    task_completion = 0
    while wait_time > 0:
        messages = receive_queue_message(
            sqs_url, sqs_client, MaxNumberOfMessages=10, wait_time=delay
        )

        alert_type = ""
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
                try:
                    subject_info = json.loads(subject)
                    sns_user_id = subject_info["user_id"]
                except Exception as e:
                    logger.error(f"Cannot parse {subject_info} from SQS {e}")
                    raise e
                if sns_user_id != worker_config.user_id:
                    continue
                # parse Message
                try:
                    message_json = json.loads(message_text)
                except Exception as e:
                    logger.error(f"Cannot parse {message_json} from SQS {e}")
                    logger.error(
                        f"Cannot parse task id. But we consider this task completed"
                    )
                    numb_tasks_completed += 1
                    continue
                try:

                    alert_type = subject_info["alert_type"]
                    task_id = message_json["task_id"]

                    if (
                        alert_type == SNSSubjectsAlert.SAVED_DATA.name
                        or alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name
                    ):
                        previous_messages_time = time.time()
                        if alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name:
                            # log out error message
                            logger.info(message_json)
                        try:
                            # print(f"task id: {task_id}")
                            if task_id in task_ids_set:
                                task_ids_set.remove(task_id)
                                numb_tasks_completed += 1
                                task_completion = int(
                                    numb_tasks_completed * 100 / total_task_length
                                )
                                logger.info(
                                    f"Complete task: {numb_tasks_completed} totl:{total_task_length} task_completion: {task_completion} %"
                                )
                        except Exception as e:
                            logger.info(f"Parse message failed {e}")
                        delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    else:
                        continue

                except Exception as e:
                    logger.warning(
                        f"Delet this {subject} !!, This subject is not json format {e}"
                    )
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
        logger.info(
            f" Waiting .: {wait_time - delay} \
            Time: {time.ctime(time.time())} "
        )
        if numb_tasks_completed == total_task_length:
            logger.info("===== All task completed ====")
            if len(task_ids_set) > 0:
                for id in task_ids_set:
                    logger.info(f"Cannot parse message from {id}!!. Somehing wrong!! ")
            return
        idle_time = time.time() - previous_messages_time
        if idle_time >= acccepted_idle_time:
            logger.info(f"===== No messages receive over time {idle_time} sec ====")
            logger.info(f"===== Number of unfinished tasks {len(task_ids_set)} ====")
            logger.info(f"===== Check tasks status directly ====")
            for id in task_ids_set:
                logger.info(f"== Check id :{id} ==")
            try:
                unfinished_tasks_set = check_tasks_status(
                    is_docker=is_docker,
                    server_name=server_name,
                    task_ids_set=task_ids_set,
                )
            except Exception as e:
                logger.error(f"Check task status failed :{e}")
                return unfinished_tasks_set
            return unfinished_tasks_set
        time.sleep(delay)
        wait_time -= int(delay)
    return task_ids_set


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
