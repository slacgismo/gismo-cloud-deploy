from .WORKER_CONFIG import WORKER_CONFIG
from typing import List
from .check_aws import connect_aws_client
from .sqs import receive_queue_message, delete_queue_message
from .eks_utils import match_hostname_from_node_name,collect_node_name_and_pod_name
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

def long_pulling_sqs_multi_server(
    worker_config: WORKER_CONFIG = None,
    delay: int = None,
    sqs_url: str = None,
    acccepted_idle_time: int = 1,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    server_list: list = None,
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

    received_init_task_ids_dict = dict()
    received_init_task_total_num_dict = dict()
    received_completed_task_ids_dict = dict()
    received_completed_task_ids_dict_comleted = dict()
    previous_received_completed_task_ids_set_len = dict()
    for server_info in server_list:
        server_name = server_info['name']
        namespace = server_info['namespace']
        received_completed_task_ids_dict_comleted[server_name] = False
        received_completed_task_ids_dict[server_name] = []
        received_init_task_ids_dict[server_name] = []
        previous_received_completed_task_ids_set_len[server_name] = 0
        received_init_task_total_num_dict[server_name] = -1

    # previous_init_task_ids_set_dict = len(
    #     received_init_task_ids_set
    # )  # flag to retrieve message again
    # previous_received_completed_task_ids_set_len = len(
    #     received_completed_task_ids_set
    # )  # flag to retrieve message again
    previous_messages_time = time.time()  # flag of idle time
    num_total_tasks = -1
    uncompleted_task_id_set = set()
    total_tasks_number = 0 
    
    # node_name = match_hostname_from_node_name(hostname=msg_dict["hostname"], pod_prefix="worker")
    match_nodemname_hostname_dict = collect_node_name_and_pod_name()
    # print(f"nodes_dict: {match_nodemname_hostname_dict}")
    is_received_init_task_ids_dict_completed= True
    start_time = time.time()
    # match_nodemname_hostname_dict = dict()
    # match_nodemname_hostname_dict = 
    while True > 0:
        messages = receive_queue_message(
            sqs_url, sqs_client, MaxNumberOfMessages=10, wait_time=delay
        )
        save_data = []
        logs_data = []
        error_data = []
        init_command_logs = []

        _message_start_time = time.time()
        if "Messages" in messages:
            # print(f"length of message: {len(messages)}")
            loog_server_start = time.time()
            for msg in messages["Messages"]:
                msg_body = msg["Body"]
                msg_dict = json.loads(msg_body)
                # print(f"msg_dict: {msg_dict}")

                receipt_handle = msg["ReceiptHandle"]
                delete_queue_message(sqs_url, receipt_handle, sqs_client)

  
                # parse Message
                previous_messages_time = time.time()


                try:
                    # message_json = json.loads(message_text)
                    alert_type = msg_dict["alert_type"]
                    
                except Exception as e:
                    logger.error("----------------------------------------")
                    logger.error(f"Cannot parse alert_type from  {msg_dict} from SQS {e}")
                    logger.error(f"Cannot parse alert_type. Delete this message")
                    logger.error("----------------------------------------")
                    # numb_tasks_completed += 1
                    
                try:
                    po_server_name = msg_dict["po_server_name"]
                except Exception as e:
                    logger.error("----------------------------------------")
                    logger.error(f"Cannot parse po_server_name from  {msg_dict} from SQS {e}")
                    logger.error(f"Cannot parse alert_type. Delete this message")
                    logger.error("----------------------------------------")
                    # numb_tasks_completed += 1
            

                # check alert type.
                # 1. if the alert type is SEND_TASKID. add taskid in received_init_task_ids_set
                if alert_type == SNSSubjectsAlert.SEND_TASKID.name:
                    
                    try:
                        received_init_id = msg_dict["task_id"]
                        send_time = msg_dict['send_time']

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
                    if po_server_name in received_init_task_ids_dict:
                        received_init_task_ids_dict[po_server_name].append(received_init_id)

                    # _num_of_total_tasks_of_server = int(msg_dict["num_total_tasks"])
                    # if _num_of_total_tasks_of_server > 0:
                    #     received_init_task_total_num_dict[po_server_name] = int(msg_dict["num_total_tasks"])
                    _receive_command = {
                        "file_name": msg_dict["file_name"],
                        "column_name": msg_dict["column_name"],
                        "task_id": msg_dict["task_id"],
                        "po_server_name": po_server_name,
                        "send_time": msg_dict["send_time"],
                        "index_file":  msg_dict["index_file"],
                        "index_colium":  msg_dict["index_colium"],
                        "repeat_number_per_round": msg_dict["repeat_number_per_round"],
                    }
                    init_command_logs.append(_receive_command)

                # 2. if the alert type is SYSTEM_ERROR, or SAVED_DATA
                # add
                _process_save_data_stat = time.time()
                if (
                    alert_type == SNSSubjectsAlert.SYSTEM_ERROR.name
                    or alert_type == SNSSubjectsAlert.SAVED_DATA.name
                ):
                    # print(f"----  SAVED_DATA: {po_server_name}----------")
                   
                    previous_messages_time
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
                    if po_server_name in received_completed_task_ids_dict:
                        received_completed_task_ids_dict[po_server_name].append(received_completed_id)
                        

                    # node_name = match_hostname_from_node_name(hostname=msg_dict["hostname"], pod_prefix="worker")
                    hostname =  msg_dict["hostname"] 
                    node_name = None
                    if hostname not in match_nodemname_hostname_dict:
                        node_name = match_hostname_from_node_name(hostname=hostname, pod_prefix="worker")
                        match_nodemname_hostname_dict[hostname] = node_name
                    else:
                        node_name = match_nodemname_hostname_dict[hostname]
                    

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
                        "po_server_name":msg_dict["po_server_name"],
                        "node_name": node_name,
                       
                    }
                    # print(f"--------logs :{_logs}")
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
                            "po_server_name":msg_dict["po_server_name"],
                            "pid": msg_dict["pid"],
                            "error": msg_dict["error"],
                        }
                        error_data.append(_error)
                    # Save data
                    if alert_type == SNSSubjectsAlert.SAVED_DATA.name:
                        save_data.append(msg_dict["data"])
                    # end_process_save_data_stat = time.time() -  _process_save_data_stat
                    # print(f'----end append save data time : {round(end_process_save_data_stat, 2)} ')
                
                if alert_type == SNSSubjectsAlert.SEND_TASKID_INFO.name:

                    try:
                        num_total_tasks = int(msg_dict["total_tasks"])
                        received_init_task_total_num_dict[po_server_name]  = num_total_tasks
                    except Exception as e:
                        logger.error(
                            "Cannot parse total task number from alert type SEND_TASKID_INFO. Chcek app.py"
                        )
                        raise Exception(
                            f"Cannot parse total tasks number from message {msg_dict} error: {e} "
                        )
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
  

            # loog_server_end = time.time() - loog_server_start
            # print(f" ***** end messages loop server :{round(loog_server_end,2)}")
            # END of receive message


        # Appand to files
        # save data
        # if len(save_data) > 0 :
        #     pickle.dump(save_data, open('save_data.p', 'wb'))
        append_receive_data(
            data_dict=init_command_logs, file_name="results/init_command_logs.csv"
        )
        append_receive_data(
            data_dict=save_data, file_name=worker_config.save_data_file_local
        )
        # # save logs
        # if len(logs_data) > 0 :
        #     pickle.dump(logs_data, open('logs.p', 'wb'))
        append_receive_data(
            data_dict=logs_data, file_name=worker_config.save_logs_file_local
        )
        # # save
        # if len(error_data) > 0 :
        #     pickle.dump(error_data, open('error.p', 'wb'))
        append_receive_data(
            data_dict=error_data, file_name=worker_config.save_error_file_local
        )
        # Invoke received new message again
  
        _is_receive_message_again = False
        # if is_received_init_task_ids_dict_completed is True:
        _totak_tasks_number_in_server = 0 
        _total_tasks_of_all_server= 0
        _current_length_tasks_of_all_server = 0
        for server_info in  server_list:
            server_name = server_info['name']
            if server_name in received_completed_task_ids_dict:
                _totak_tasks_number_in_server = int(received_init_task_total_num_dict[server_name])
                _current_complete_tasks_in_server = len(received_completed_task_ids_dict[server_name])
                _total_tasks_of_all_server += _totak_tasks_number_in_server
                _current_length_tasks_of_all_server += _current_complete_tasks_in_server
                if _totak_tasks_number_in_server  > 0  and _totak_tasks_number_in_server == _current_complete_tasks_in_server:
                    received_completed_task_ids_dict_comleted[server_name] = True
                    
                    # logger.info(f" server_name : {server_name } _totak_tasks_number_in_server:{_totak_tasks_number_in_server} compelted")
                else:
                    task_completion = 0
                    if _totak_tasks_number_in_server > 0:
                        
                        task_completion = int(_current_complete_tasks_in_server * 100 / _totak_tasks_number_in_server)

                    # logger.info(f" server_name : {server_name } _totak_tasks_number_in_server:{_totak_tasks_number_in_server} _current_complete_tasks_in_server : {_current_complete_tasks_in_server} task_completion: {task_completion} %")

                if previous_received_completed_task_ids_set_len[server_name] != _current_complete_tasks_in_server :
                    _is_receive_message_again = True
                    previous_received_completed_task_ids_set_len[server_name] = _current_complete_tasks_in_server
      
        if _total_tasks_of_all_server > 0 :
            all_task_completion = int(_current_length_tasks_of_all_server * 100 / _total_tasks_of_all_server)
            logger.info(f"Tasks: {_current_length_tasks_of_all_server} / {_total_tasks_of_all_server} Completeion: {all_task_completion} %")

        if _is_receive_message_again is True:
            
            # loop_time = time.time() -  _message_start_time 
            # print(f"Receive message again :{round(loop_time,2)}")
            time.sleep(0.1)
            continue

   
            
        _is_all_tasks_completed = True

        for server_info in server_list:
            server_name = server_info['name']
            if received_completed_task_ids_dict_comleted[server_name] is False:
                _is_all_tasks_completed = False
                break
        if _is_all_tasks_completed is True:
            # total_tasks_number = 0 
            # if server_name in received_completed_task_ids_dict:
            #     _totak_tasks_number_in_server = int(received_init_task_total_num_dict[server_name])
            #     total_tasks_number +=  _totak_tasks_number_in_server
            logger.info(f"All tasks completed :{_total_tasks_of_all_server}")
            return
        
        # # Handle over time
        idle_time = time.time() - previous_messages_time
        if idle_time >= acccepted_idle_time:
            uncompleted_task_length = _total_tasks_of_all_server - _current_length_tasks_of_all_server
            logger.info(f"===== No messages receive over time {idle_time} sec ====")
            logger.info(
                f"===== Number of unfinished tasks {uncompleted_task_length} ===="
            )
            return uncompleted_task_length

        total_time = time.time() - start_time
        logger.info(
            f" total_time .: {total_time} \
            Idle Time: {idle_time} "
        )
        time.sleep(1)
        # wait_time -= int(delay)

    return uncompleted_task_id_set







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
                        send_time = msg_dict['send_time']
                   
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
                    node_name = match_hostname_from_node_name(hostname=msg_dict["hostname"], pod_prefix="worker")
                    # print("-------------------")
                    # print(f"node_name: {node_name}")
                    # print("-------------------")
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
                        "node_name": node_name
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
    # print(f"<----->save files {file_name}  data_dict:{data_dict}")
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
