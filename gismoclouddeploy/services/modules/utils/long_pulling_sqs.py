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
    save_performance_file_local: str = None,
    save_plot_file_local: str = None,
) -> None:

    # remove previous save data
    if exists(save_data_file_local):
        os.remove(save_data_file_local)

    if exists(save_logs_file_local):
        os.remove(save_logs_file_local)

    if exists(save_error_file_local):
        os.remove(save_error_file_local)

    if exists(save_performance_file_local):
        os.remove(save_performance_file_local)

    if exists(save_plot_file_local):
        os.remove(save_plot_file_local)


def long_pulling_sqs(
    worker_config: WORKER_CONFIG = None,
    delay: int = None,
    sqs_url: str = None,
    acccepted_idle_time: int = 1,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:

    # task_ids_set = set(task_ids)
    # total_task_length = len(task_ids_set)
    sqs_client = connect_aws_client(
        client_name="sqs",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )

    task_completion = 0

    remove_prevous_results_files(
        save_data_file_local=worker_config.save_data_file_local,
        save_logs_file_local=worker_config.save_logs_file_local,
        save_error_file_local=worker_config.save_error_file_local,
        save_performance_file_local=worker_config.save_performance_local,
        save_plot_file_local=worker_config.save_plot_file_local,
    )
    is_receive_task_info = False

    received_init_task_ids_set = set()
    received_completed_task_ids_set = set()
    previous_init_task_ids_set_len = len(
        received_init_task_ids_set
    )  # flag to retrieve message again
    previous_received_completed_task_ids_set_len = len(
        received_completed_task_ids_set
    )  # flag to retrieve message again
    previous_messages_time = time.time()  # flag of idle time
    num_total_tasks = -1
    uncompleted_task_id_set = set()

    start_time = time.time()
    while True > 0:
        messages = receive_queue_message(
            sqs_url, sqs_client, MaxNumberOfMessages=10, wait_time=delay
        )
        save_data = []
        logs_data = []
        error_data = []
        if "Messages" in messages:
            for msg in messages["Messages"]:
                msg_body = msg["Body"]
                msg_dict = json.loads(msg_body)
                # print("------------->")
                # print(msg_dict)
                receipt_handle = msg["ReceiptHandle"]
                # subject = (
                #     msg_body["Subject"].strip("'<>() ").replace("'", '"').strip("\n")
                # )
                # message_text = (
                #     msg_body["Message"].strip("'<>() ").replace("'", '"').strip("\n")
                # )
                # logger.info(f"subject: {subject}")
                # logger.info(f"message_text: {message_text}")
                MessageAttributes = msg["MessageAttributes"]
                user_id = MessageAttributes["user_id"]["StringValue"]
                if user_id != worker_config.user_id:
                    # not this user's sqs message. do touch
                    continue
                # parse Message
                previous_messages_time = time.time()

                try:
                    # message_json = json.loads(message_text)
                    alert_type = msg_dict["alert_type"]
                except Exception as e:
                    logger.error("----------------------------------------")
                    logger.error(f"Cannot parse {msg_dict} from SQS {e}")
                    logger.error(f"Cannot parse alert_type. Delete this message")
                    logger.error("----------------------------------------")
                    # numb_tasks_completed += 1
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    continue

                # check alert type.
                # 1. if the alert type is SEND_TASKID. add taskid in received_init_task_ids_set
                if alert_type == SNSSubjectsAlert.SEND_TASKID.name:

                    try:
                        received_init_id = msg_dict["task_id"]
                    except:
                        logger.warning(
                            "------------------------------------------------------"
                        )
                        logger.warning(
                            f"This message does not contain task_id {msg_dict}"
                        )
                        logger.warning(
                            "------------------------------------------------------"
                        )

                    # Get task_id
                    received_init_task_ids_set.add(received_init_id)

                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    continue

                # 2. if the alert type is SYSTEM_ERROR, or SAVED_DATA
                # add
                if (
                    alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name
                    or alert_type == SNSSubjectsAlert.SAVED_DATA.name
                ):
                    try:
                        received_completed_id = msg_dict["task_id"]
                    except:
                        logger.warning(
                            "------------------------------------------------------"
                        )
                        logger.warning(
                            f"This message does not contain task_id {msg_dict}"
                        )
                        logger.warning(
                            "------------------------------------------------------"
                        )

                    received_completed_task_ids_set.add(received_completed_id)
                    # Save loags
                    # file_name,column_name,task_id,alert_type,start_time,end_time,hostname,host_ip,pid,error
                    _logs = {
                        "file_name": msg_dict["file_name"],
                        "column_name": msg_dict["column_name"],
                        "task_id": msg_dict["task_id"],
                        "start_time": msg_dict["start_time"],
                        "end_time": msg_dict["end_time"],
                        "hostname": msg_dict["hostname"],
                        "host_ip": msg_dict["host_ip"],
                        "pid": msg_dict["pid"],
                        "alert_type": msg_dict["alert_type"],
                    }
                    logs_data.append(_logs)
                    # Save errors
                    if alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name:
                        _error = {
                            "file_name": msg_dict["file_name"],
                            "column_name": msg_dict["column_name"],
                            "task_id": msg_dict["task_id"],
                            "start_time": msg_dict["start_time"],
                            "end_time": msg_dict["end_time"],
                            "hostname": msg_dict["hostname"],
                            "host_ip": msg_dict["host_ip"],
                            "pid": msg_dict["pid"],
                            "error": msg_dict["error"],
                        }
                        error_data.append(_error)
                    # Save data
                    if alert_type == SNSSubjectsAlert.SAVED_DATA.name:
                        save_data.append(msg_dict["data"])
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    continue

                if alert_type == SNSSubjectsAlert.SEND_TASKID_INFO.name:
                    is_receive_task_info = True
                    try:
                        num_total_tasks = int(msg_dict["total_tasks"])
                    except Exception as e:
                        logger.error(
                            "Cannot parse total task number from alert type SEND_TASKID_INFO. Chcek app.py"
                        )
                        raise Exception(
                            f"Cannot parse total tasks number from message {msg_dict} error: {e} "
                        )
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    continue

            # end of loop

        # Appand to files
        # save data
        append_receive_data(
            data_dict=save_data, file_name=worker_config.save_data_file_local
        )
        # save logs
        append_receive_data(
            data_dict=logs_data, file_name=worker_config.save_logs_file_local
        )
        # save
        append_receive_data(
            data_dict=error_data, file_name=worker_config.save_error_file_local
        )

        # Invoke received new message again
        if previous_received_completed_task_ids_set_len != len(
            received_completed_task_ids_set
        ) or previous_init_task_ids_set_len != len(received_init_task_ids_set):
            previous_init_task_ids_set_len = len(received_init_task_ids_set)
            previous_received_completed_task_ids_set_len = len(
                received_completed_task_ids_set
            )
            logger.info(
                f"Init task: {previous_init_task_ids_set_len}. Completed task: {previous_received_completed_task_ids_set_len}"
            )
            time.sleep(0.1)
            # don't wait ,get messages again
            continue

        # Task completion
        if is_receive_task_info:
            # calculate task completion.

            num_completed_task = len(received_completed_task_ids_set)
            if num_total_tasks > 0:
                task_completion = int(num_completed_task * 100 / num_total_tasks)
            logger.info(
                f"{num_completed_task} tasks completed. Total task:{num_total_tasks}. Completion:{task_completion} %"
            )

            if len(received_completed_task_ids_set) == len(
                received_init_task_ids_set
            ) and num_total_tasks == len(received_init_task_ids_set):
                # all task completed
                logger.info("===== All task completed ====")
                # save data
                return uncompleted_task_id_set
            # in case of comleted task id > received_init_task_ids_set
            if len(received_completed_task_ids_set) > len(
                received_init_task_ids_set
            ) and num_total_tasks == len(received_init_task_ids_set):
                logger.error("Something wrong !!! ")
                for completed_id in received_completed_task_ids_set:
                    if completed_id in received_init_task_ids_set:
                        continue
                    else:
                        logger.error(
                            f"{completed_id} does not exist in received_init_task_ids_set. Something Wroing !!!!"
                        )
                        uncompleted_task_id_set.add(completed_id)
                return uncompleted_task_id_set

        # Handle over time
        idle_time = time.time() - previous_messages_time
        if idle_time >= acccepted_idle_time:
            logger.info(f"===== No messages receive over time {idle_time} sec ====")

            for id in received_init_task_ids_set:
                if id in received_completed_task_ids_set:
                    continue
                uncompleted_task_id_set.add(id)

            logger.info(
                f"===== Number of unfinished tasks {len(uncompleted_task_id_set)} ===="
            )
            return uncompleted_task_id_set

        total_time = time.time() - start_time
        logger.info(
            f" total_time .: {total_time} \
            Idle Time: {idle_time} "
        )
        time.sleep(delay)
        # wait_time -= int(delay)

    return uncompleted_task_id_set


def append_receive_data(
    data_dict: dict = None,
    file_name: str = None,
) -> None:
    if len(data_dict) == 0:
        return

    try:
        if len(data_dict) > 0:
            save_data_df = pd.json_normalize(data_dict)
            save_data_df.to_csv(
                file_name,
                mode="a",
                header=not os.path.exists(file_name),
            )
    except Exception as e:
        raise e
