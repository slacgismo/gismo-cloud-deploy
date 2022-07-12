
from .WORKER_CONFIG import WORKER_CONFIG
from typing import List, Set
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




def long_pulling_sqs(
    worker_config: WORKER_CONFIG = None,
    servers_list:Set[str] = None,
    wait_time: int = 1,
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

    received_init_task_ids_dict = dict()
    received_completed_task_ids_dict = dict()
    is_received_completed_task_ids_completed = dict()
    num_total_tasks_dict = dict()
    # assigned 
    # previous_init_task_ids_dict_len = dict()
    # received_completed_task_ids_dict_len = dict()
    is_received_init_task_ids_completed = dict()
    for sever in servers_list:
        server_name = sever['name']
        print()
        received_init_task_ids_dict[server_name] = set()
        received_completed_task_ids_dict[server_name] = set()
        is_received_init_task_ids_completed[server_name] = False
        num_total_tasks_dict[server_name] = 0
        is_received_completed_task_ids_completed[server_name] = False
        # previous_init_task_ids_dict_len[server_name] = 0
        # received_completed_task_ids_dict_len[server_name] = 0
    logger.info("============= received_init_task_ids_dict ")
    for key , value in received_init_task_ids_dict.items():
        print(key, value)
    logger.info("============= received_completed_task_ids_dict")
    for key , value in received_completed_task_ids_dict.items():
        print(key, value)
    # for server in servers_list:
  
 


    # received_init_task_ids_set = set()
    # received_completed_task_ids_set = set()
    # previous_init_task_ids_set_len = len(
    #     received_init_task_ids_set
    # )  # flag to retrieve message again
    # previous_received_completed_task_ids_set_len = len(
    #     received_completed_task_ids_set
    # )  # flag to retrieve message again
    previous_messages_time = time.time()  # flag of idle time
    # num_total_tasks = -1
    # uncompleted_task_id_set = set()
    is_receive_task_info_completed = False
    is_receive_all_tasks_completed = False
    while wait_time > 0:
        messages = receive_queue_message(
            sqs_url, sqs_client, MaxNumberOfMessages=10, wait_time=delay
        )
        save_data = []
        logs_data = []
        error_data = []

        # Parse receive messages
        if "Messages" in messages:
            for msg in messages["Messages"]:
                msg_body = json.loads(msg["Body"])
                logger.info(msg_body)
                receipt_handle = msg["ReceiptHandle"]
                subject = (
                    msg_body["Subject"].strip("'<>() ").replace("'", '"').strip("\n")
                )
                message_text = (
                    msg_body["Message"].strip("'<>() ").replace("'", '"').strip("\n")
                )
                # logger.info(f"subject: {subject}")
                # logger.info(f"message_text: {message_text}")

                if subject != worker_config.user_id:
                    # not this user's sqs message. do nothing 
                    logger.info(f"===========================")
                    logger.info(f"Not my message {subject}")
                    logger.info(f"===========================")
                    continue
                
                # Messaage belong to me

                # parse Message
                previous_messages_time = time.time()

                try:
                    message_json = json.loads(message_text)
                    logger.info("-------------")
                    logger.info(message_json)
                    logger.info("-------------")
                    alert_type = message_json["alert_type"]
                except Exception as e:
                    logger.error("----------------------------------------")
                    logger.error(f"Cannot parse {message_json} from SQS {e}")
                    logger.error(f"Cannot parse alert_type. Delete this message")
                    logger.error("----------------------------------------")
                    # numb_tasks_completed += 1
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    continue
                
                # parse server name . 


                try:
                    server_name =  message_json["server_name"]
                   
                except Exception as e :
                    raise Exception (f"No server_name in message {e}")
                
                # check server name exist
                if (server_name in received_init_task_ids_dict )is False or (server_name in received_completed_task_ids_dict) is False:
                    raise Exception(f"{server_name} does not exist in server list")
                    
                
                # check alert type.
                # 1. if the alert type is SEND_TASKID. add taskid in received_init_task_ids_set
                if alert_type == SNSSubjectsAlert.SEND_TASKID.name:
                    
                    try:
                        received_init_id = message_json["task_id"]
                    except:
                        logger.warning(
                            "------------------------------------------------------"
                        )
                        logger.warning(
                            f"This message does not contain task_id {message_json}"
                        )
                        logger.warning(
                            "------------------------------------------------------"
                        )

                    received_init_task_ids_dict[server_name].add(received_init_id)

                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    
                    continue

                # 2. if the alert type is SYSTEM_ERROR, or SAVED_DATA
                # add
                if (
                    alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name
                    or alert_type == SNSSubjectsAlert.SAVED_DATA.name
                ):
                    try:
                        received_completed_id = message_json["task_id"]
                    except:
                        logger.warning(
                            "------------------------------------------------------"
                        )
                        logger.warning(
                            f"This message does not contain task_id {message_json}"
                        )
                        logger.warning(
                            "------------------------------------------------------"
                        )

                    received_completed_task_ids_dict[server_name].add(received_completed_id)
                    # Save loags
                    logs_data.append(message_json)
                    # Save errors
                    if alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name:
                        error_data.append(message_json)
                    # Save data
                    if alert_type == SNSSubjectsAlert.SAVED_DATA.name:
                        save_data.append(message_json)
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    continue

                if alert_type == SNSSubjectsAlert.SEND_TASKID_INFO.name:
                    is_receive_task_info = True
                    try:
                        _num_total_tasks = message_json["total_tasks"]
                        # update flag 
                        is_received_init_task_ids_completed[server_name] = True
                        num_total_tasks_dict[server_name] = _num_total_tasks
                    except Exception as e:
                        logger.error(
                            "Cannot parse total task number from alert type SEND_TASKID_INFO. Chcek app.py"
                        )
                        raise Exception(
                            f"Cannot parse total tasks number from message {message_json} error: {e} "
                        )
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                    continue

            # end of loop

        # Appand to files
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

        # Invoke received new message again
        # for key, value in previous_init_task_ids_dict_len.items():     

        # if previous_received_completed_task_ids_set_len != len(
        #     received_completed_task_ids_set
        # ) or previous_init_task_ids_set_len != len(received_init_task_ids_set):
        #     previous_init_task_ids_set_len = len(received_init_task_ids_set)
        #     previous_received_completed_task_ids_set_len = len(
        #         received_completed_task_ids_set
        #     )
        #     logger.info(
        #         f"Init task: {previous_init_task_ids_set_len}. Completed task: {previous_received_completed_task_ids_set_len}"`  
        #     )
        #     time.sleep(0.1)
        #     # don't wait ,get messages again
        #     continue

        # Task completion
        is_receive_task_info_completed = True
        for key, value in is_received_init_task_ids_completed.items():
           
            if value is False:
                # if any of the value is false . The receive info is not completed
                is_receive_task_info_completed = False
                break
            
 

        if is_receive_task_info_completed is True:
            # consider receive info completed
            # calculate task completion of each server
            for key, value in received_completed_task_ids_dict.items():
                server_name = key
                num_completed_task = len(value)
                number_of_total_tasks = num_total_tasks_dict[key]
                if number_of_total_tasks > 0:
                    task_completion = int(num_completed_task * 100 / number_of_total_tasks)
                    logger.info(f"server: {server_name}: {num_completed_task} tasks completed. Total task:{number_of_total_tasks} Completion:{task_completion} %.")
                
                if num_completed_task == number_of_total_tasks:
                    is_received_completed_task_ids_completed[key] = True

            is_receive_all_tasks_completed = True
            for key, value in is_received_completed_task_ids_completed.items():
                if value is False:
                    is_receive_all_tasks_completed = False
                    break
                


            if is_receive_all_tasks_completed is True:
                logger.info("===== All task completed ====")
                return None

        # Handle over time
        idle_time = time.time() - previous_messages_time
        if idle_time >= acccepted_idle_time:
            logger.info(f"===== No messages receive over time {idle_time} sec ====")
            unfinished_tasks = dict()
            for key, value in received_completed_task_ids_dict.items():
                _init_id_set = received_init_task_ids_dict[key]
                _unfinished_set = value.difference(_init_id_set)
                unfinished_tasks[key] = _unfinished_set
            
            for key , value in unfinished_tasks:
                logger.info(f"server :{key}, unfinished :{value}")
            return 
    
        # delay 
        logger.info(
            f" Waiting .: {wait_time - delay} \
            Idle Time: {idle_time} "
        )
        time.sleep(delay)
        wait_time -= int(delay)

    return None

# def long_pulling_sqs(
#     worker_config: WORKER_CONFIG = None,
#     wait_time: int = 1,
#     delay: int = None,
#     sqs_url: str = None,
#     acccepted_idle_time: int = 1,
#     aws_access_key: str = None,
#     aws_secret_access_key: str = None,
#     aws_region: str = None,
# ) -> None:

#     # task_ids_set = set(task_ids)
#     # total_task_length = len(task_ids_set)
#     sqs_client = connect_aws_client(
#         client_name="sqs",
#         key_id=aws_access_key,
#         secret=aws_secret_access_key,
#         region=aws_region,
#     )

#     numb_tasks_completed = 0
#     task_completion = 0

#     remove_prevous_results_files(
#         save_data_file_local=worker_config.save_data_file_local,
#         save_logs_file_local=worker_config.save_logs_file_local,
#         save_error_file_local=worker_config.save_error_file_local,
#         save_performance_file_local=worker_config.save_performance_local,
#         save_plot_file_local=worker_config.save_plot_file_local,
#     )
#     is_receive_task_info = False

#     received_init_task_ids_set = set()
#     received_completed_task_ids_set = set()
#     previous_init_task_ids_set_len = len(
#         received_init_task_ids_set
#     )  # flag to retrieve message again
#     previous_received_completed_task_ids_set_len = len(
#         received_completed_task_ids_set
#     )  # flag to retrieve message again
#     previous_messages_time = time.time()  # flag of idle time
#     num_total_tasks = -1
#     uncompleted_task_id_set = set()

#     while wait_time > 0:
#         messages = receive_queue_message(
#             sqs_url, sqs_client, MaxNumberOfMessages=10, wait_time=delay
#         )
#         save_data = []
#         logs_data = []
#         error_data = []
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
#                 # logger.info(f"subject: {subject}")
#                 # logger.info(f"message_text: {message_text}")

#                 if subject != worker_config.user_id:
#                     # not this user's sqs message. do touch
#                     continue
#                 # parse Message
#                 previous_messages_time = time.time()

#                 try:
#                     message_json = json.loads(message_text)
#                     alert_type = message_json["alert_type"]
#                 except Exception as e:
#                     logger.error("----------------------------------------")
#                     logger.error(f"Cannot parse {message_json} from SQS {e}")
#                     logger.error(f"Cannot parse alert_type. Delete this message")
#                     logger.error("----------------------------------------")
#                     # numb_tasks_completed += 1
#                     delete_queue_message(sqs_url, receipt_handle, sqs_client)
#                     continue

#                 # check alert type.
#                 # 1. if the alert type is SEND_TASKID. add taskid in received_init_task_ids_set
#                 if alert_type == SNSSubjectsAlert.SEND_TASKID.name:

#                     try:
#                         received_init_id = message_json["task_id"]
#                     except:
#                         logger.warning(
#                             "------------------------------------------------------"
#                         )
#                         logger.warning(
#                             f"This message does not contain task_id {message_json}"
#                         )
#                         logger.warning(
#                             "------------------------------------------------------"
#                         )

#                     received_init_task_ids_set.add(received_init_id)

#                     delete_queue_message(sqs_url, receipt_handle, sqs_client)
#                     continue

#                 # 2. if the alert type is SYSTEM_ERROR, or SAVED_DATA
#                 # add
#                 if (
#                     alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name
#                     or alert_type == SNSSubjectsAlert.SAVED_DATA.name
#                 ):
#                     try:
#                         received_completed_id = message_json["task_id"]
#                     except:
#                         logger.warning(
#                             "------------------------------------------------------"
#                         )
#                         logger.warning(
#                             f"This message does not contain task_id {message_json}"
#                         )
#                         logger.warning(
#                             "------------------------------------------------------"
#                         )

#                     received_completed_task_ids_set.add(received_completed_id)
#                     # Save loags
#                     logs_data.append(message_json)
#                     # Save errors
#                     if alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name:
#                         error_data.append(message_json)
#                     # Save data
#                     if alert_type == SNSSubjectsAlert.SAVED_DATA.name:
#                         save_data.append(message_json)
#                     delete_queue_message(sqs_url, receipt_handle, sqs_client)
#                     continue

#                 if alert_type == SNSSubjectsAlert.SEND_TASKID_INFO.name:
#                     is_receive_task_info = True
#                     try:
#                         num_total_tasks = message_json["total_tasks"]
#                     except Exception as e:
#                         logger.error(
#                             "Cannot parse total task number from alert type SEND_TASKID_INFO. Chcek app.py"
#                         )
#                         raise Exception(
#                             f"Cannot parse total tasks number from message {message_json} error: {e} "
#                         )
#                     delete_queue_message(sqs_url, receipt_handle, sqs_client)
#                     continue

#             # end of loop

#         # Appand to files
#         if len(save_data) > 0:
#             save_data_df = pd.json_normalize(save_data)
#             save_data_df.to_csv(
#                 worker_config.save_data_file_local,
#                 mode="a",
#                 header=not os.path.exists(worker_config.save_data_file_local),
#             )
#         if len(error_data) > 0:
#             save_error_df = pd.json_normalize(error_data)
#             save_error_df.to_csv(
#                 worker_config.save_error_file_local,
#                 mode="a",
#                 header=not os.path.exists(worker_config.save_error_file_local),
#             )
#         if len(logs_data) > 0:
#             save_logs_df = pd.json_normalize(logs_data)
#             save_logs_df.to_csv(
#                 worker_config.save_logs_file_local,
#                 mode="a",
#                 header=not os.path.exists(worker_config.save_logs_file_local),
#             )

#         # Invoke received new message again
#         if previous_received_completed_task_ids_set_len != len(
#             received_completed_task_ids_set
#         ) or previous_init_task_ids_set_len != len(received_init_task_ids_set):
#             previous_init_task_ids_set_len = len(received_init_task_ids_set)
#             previous_received_completed_task_ids_set_len = len(
#                 received_completed_task_ids_set
#             )
#             logger.info(
#                 f"Init task: {previous_init_task_ids_set_len}. Completed task: {previous_received_completed_task_ids_set_len}"
#             )
#             time.sleep(0.1)
#             # don't wait ,get messages again
#             continue

#         # Task completion
#         if is_receive_task_info:
#             # calculate task completion.

#             num_completed_task = len(received_completed_task_ids_set)
#             if num_total_tasks > 0:
#                 task_completion = int(num_completed_task * 100 / num_total_tasks)
#             logger.info(
#                 f"{num_completed_task} tasks completed. Total task:{num_total_tasks}. Completion:{task_completion} %"
#             )

#             if len(received_completed_task_ids_set) == len(
#                 received_init_task_ids_set
#             ) and num_total_tasks == len(received_init_task_ids_set):
#                 # all task completed
#                 logger.info("===== All task completed ====")
#                 # save data
#                 return uncompleted_task_id_set
#             # in case of comleted task id > received_init_task_ids_set
#             if len(received_completed_task_ids_set) > len(
#                 received_init_task_ids_set
#             ) and num_total_tasks == len(received_init_task_ids_set):
#                 logger.error("Something wrong !!! ")
#                 for completed_id in received_completed_task_ids_set:
#                     if completed_id in received_init_task_ids_set:
#                         continue
#                     else:
#                         logger.error(
#                             f"{completed_id} does not exist in received_init_task_ids_set. Something Wroing !!!!"
#                         )
#                         uncompleted_task_id_set.add(completed_id)
#                 return uncompleted_task_id_set

#         # Handle over time
#         idle_time = time.time() - previous_messages_time
#         if idle_time >= acccepted_idle_time:
#             logger.info(f"===== No messages receive over time {idle_time} sec ====")

#             for id in received_init_task_ids_set:
#                 if id in received_completed_task_ids_set:
#                     continue
#                 uncompleted_task_id_set.add(id)

#             logger.info(
#                 f"===== Number of unfinished tasks {len(uncompleted_task_id_set)} ===="
#             )
#             return uncompleted_task_id_set

#         logger.info(
#             f" Waiting .: {wait_time - delay} \
#             Idle Time: {idle_time} "
#         )
#         time.sleep(delay)
#         wait_time -= int(delay)

#     return uncompleted_task_id_set


def remove_prevous_results_files(
    save_data_file_local: str = None,
    save_logs_file_local: str = None,
    save_error_file_local: str = None,
    save_performance_file_local: str = None,
    save_plot_file_local: str = None,
) -> None:

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