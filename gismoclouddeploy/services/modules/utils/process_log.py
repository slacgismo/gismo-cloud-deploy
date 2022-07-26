from asyncio.log import logger
from genericpath import exists
import os
import pandas as pd

from typing import List
from modules.utils.eks_utils import match_pod_ip_to_node_name
import statistics

import datetime
from terminaltables import AsciiTable

import plotly.express as px
import plotly.io as pio
import botocore


def process_df_for_gantt(df: pd):

    worker_dict = {}

    for row in df.itertuples(index=True, name="Pandas"):
        task_id = str(row.task_id)
        start = row.start_time
        end = row.end_time
        duration = end - start
        host_ip = row.host_ip
        pid = row.pid
        task = row.file_name + "/" + row.column_name
        worker_dict[task_id] = {
            "start": start,
            "end": end,
            "duration": duration,
            "host_ip": host_ip,
            "pid": pid,
            "task": task,
        }

    return worker_dict


def process_logs_from_local(
    logs_file_path_name_local: str = None,
    saved_image_name_local: str = None,
    s3_client: "botocore.client.S3" = None,
) -> bool:
    if exists(logs_file_path_name_local) is False:
        logger.error(f"{logs_file_path_name_local} does not exist")
        return False

    df = pd.read_csv(logs_file_path_name_local)

    pods_name_prefix_set = ("worker", "webapp")
    pods_info_dict = match_pod_ip_to_node_name(pods_name_prefix_set)
    # print(pods_info_dict)
    worker_dict = process_df_for_gantt(df)
    # # # # Show dataframe
    gantt_list = []
    for key, value in worker_dict.items():
        try:
            pod_ip = value["host_ip"]
            node_name = ""
            # get node name
            if pod_ip in pods_info_dict:
                node_name = pods_info_dict[pod_ip]["NOD_NAME"]

            task = f"{node_name}: {value['host_ip']}: {value['pid']}"
            if "duration" in value:
                label = f"{value['task']}: duration:{value['duration']}s"
            try:
                start_time = datetime.datetime.fromtimestamp(
                    (value["start"])
                ).isoformat()
                end_time = datetime.datetime.fromtimestamp((value["end"])).isoformat()
            except Exception as e:
                logger.error(f"error {e}")
                raise e

            item = dict(
                Task=task,
                Start=start_time,
                Finish=end_time,
                Resource=value["task"],
                Node=node_name,
                Label=label,
                Host=value["host_ip"],
                Duration=value["duration"],
            )
        except Exception as e:
            # logger.warning(f"Missing Key {e} in {value}")
            continue
        gantt_list.append(item)
    gantt_df = pd.DataFrame(gantt_list)
    fig = px.timeline(gantt_df, x_start="Start", x_end="Finish", y="Task", color="Node")
    fig.update_yaxes(
        autorange="reversed"
    )  # otherwise tasks are listed from the bottom up

    pio.write_image(
        fig, saved_image_name_local, format="png", scale=1, width=2400, height=1600
    )
    return True


def read_all_csv_from_s3_and_parse_dates_from(
    bucket_name: str = None,
    file_path_name: str = None,
    s3_client=None,
    dates_column_name=None,
    index_col=0,
) -> pd.DataFrame:

    if (
        bucket_name is None
        or file_path_name is None
        or s3_client is None
        or dates_column_name is None
    ):
        return
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)
    except Exception as e:
        print(f"error read  file: {file_path_name} error:{e}")
        raise e
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        result_df = pd.read_csv(
            response.get("Body"),
            index_col=index_col,
            parse_dates=["timestamp"],
            infer_datetime_format=True,
        )
        # print(result_df.head())
        result_df["timestamp"] = pd.to_datetime(result_df["timestamp"], unit="s")

    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df


def analyze_signle_local_logs_file(
    logs_file_path_name: str = None,
    instanceType: str = None,
    initial_process_time: float = 0,
    total_process_time: float = 0,
    eks_nodes_number: int = 0,
    num_workers: int = 0,
    num_unfinished_tasks: int = 0,
    code_templates_folder: str = None,
) -> dict:

    if exists(logs_file_path_name) is False:
        logger.error(f"{logs_file_path_name} does not exist")
        return

    df = pd.read_csv(logs_file_path_name)

    error_task = df[(df["alert_type"] == "SYSTEM_ERROR")]
    num_error_task = len(error_task)
    
    worker_dict = process_df_for_gantt(df)
    shortest_task = ""
    longest_task = ""
    min_duration = float("inf")
    max_duration = 0
    tasks_durtaion_sum = 0
    average_task_duration = 0
    total_tasks = 0
    min_start = float("inf")
    max_end = 0
    duration = 0
    task_duration_in_parallelism = 0
    efficiency = 0
    for key, value in worker_dict.items():
        # logger.info(f"ip {value['host_ip']} ")
        # logger.info(f"ip {value} ")
        if ("start" in value) is False:
            logger.warning(f"missing 'start' key in task {key}")
            continue
        if ("end" in value) is False:
            logger.warning(f"missing 'end' key in task {key}")
            continue
        start = float(value["start"])
        end = float(value["end"])
        duration = value["duration"]
        task = value["task"]
        if task == "loop_tasks_status_task":
            continue
        tasks_durtaion_sum += duration
        if start < min_start:
            min_start = start
        if end > max_end:
            max_end = end

        if duration < min_duration:
            min_duration = duration
            shortest_task = task
        if duration > max_duration:
            max_duration = duration
            longest_task = task
        total_tasks += 1
    task_duration_in_parallelism = max_end - min_start
    if total_tasks > 0:
        average_task_duration = tasks_durtaion_sum / total_tasks
    else:
        average_task_duration = tasks_durtaion_sum

    if task_duration_in_parallelism > 0:
        efficiency = int(
            (
                (tasks_durtaion_sum - task_duration_in_parallelism)
                / task_duration_in_parallelism
            )
            * 100
        )

    ip_accumulation_druations = dict()
    # --------------------------
    # calcuate effeciency factor
    # --------------------------
    # step 1 , accumulate the process time of each host_ip/pid
    for key, value in worker_dict.items():
        _duration = float(value["duration"])
        _host_ip = value['host_ip']
        _pid = value['pid']
        key = str(_host_ip) + "/" +str(_pid)
        if  key in ip_accumulation_druations:
            ip_accumulation_druations[key] += _duration
        else:
            ip_accumulation_druations[key] =  _duration


    # step 2 ,divide the total_process_time of each  host_ip/pid with task_duration_in_parallelism
    # ( total_process_time ) / (task_duration_in_parallelism * number_host_ip_pid)
    accumulated_process_duration = 0
    for key , value in ip_accumulation_druations.items():
        accumulated_process_duration += value
    effeciency_of_each_ip_pid = dict()
    effeciencyFactor = 0 
    if task_duration_in_parallelism > 0 :

        for key , value in ip_accumulation_druations.items():
            effeciency_of_each_ip_pid[key] = value/task_duration_in_parallelism

    if len(ip_accumulation_druations)> 0 :
        effeciencyFactor = accumulated_process_duration/(task_duration_in_parallelism * len(ip_accumulation_druations))

        # logger.info(f"ip {value['host_ip']}, start: {start}, end: {end} ")
    # --------------------------
    # calcuate effeciency factor
    # -------------------------- 
   
    performance_dict = {
        "file" : logs_file_path_name,
        "total_tasks": total_tasks,
        "average_task_duration": average_task_duration,
        "min_duration": min_duration,
        "max_duration":max_duration,
        "num_error_task":num_error_task,
        "longest_task":longest_task,
        "shortest_task":shortest_task,
        "num_unfinished_tasks":num_unfinished_tasks,
        "task_duration_in_parallelism":task_duration_in_parallelism,
        "tasks_durtaion_sum":tasks_durtaion_sum,
        "initial_process_time":initial_process_time,
        "total_process_time":total_process_time,
        "effeciencyFactor":effeciencyFactor
        }
    return performance_dict

def analyze_all_local_logs_files(
    logs_file_path: str = None,
    instanceType: str = None,
    init_process_time_list: float = 0,
    total_proscee_time_list: float = 0,
    eks_nodes_number: int = 0,
    num_workers: int = 0,
    save_file_path_name: str = None,
    num_unfinished_tasks: int = 0,
    code_templates_folder: str = None,
    repeat_number:int = 1,
) -> List[str]:
    if os.path.isdir(logs_file_path) is False:
        raise Exception(f"{logs_file_path} not exist")
    logs_files_list= []
    for _file in os.listdir(logs_file_path):
        prefix = _file.split("-")[0]
        if prefix == "logs":
            logs_files_list.append(_file)
    performance_list = []
    header = ["Performance"]
    file_name = ["File name"]
    average_task_duration = ["average_task_duration"]
    min_duration = ['min_duration']
    max_duration = ['max_duration']
    num_error_task = ['num_error_task']
    num_unfinished_tasks = ['num_unfinished_tasks']
    shortest_task =['shortest_task']
    longest_task = ['longest_task']
    task_duration_in_parallelism = ['task_duration_in_parallelism']
    tasks_durtaion_sum = ['tasks_durtaion_sum']
    initial_process_time = ['initial_process_time']
    total_process_time = ['total_process_time']
    effeciencyFactor = ['effeciencyFactor']
    total_tasks =  ['total_tasks']

    index = 0 
    for logs_file in logs_files_list:
        logger.info(f"Porcess {logs_file}")
        logs_path_name = logs_file_path +"/" +logs_file
        per_dict = analyze_signle_local_logs_file(
            logs_file_path_name = logs_path_name,
            instanceType=instanceType,
            initial_process_time=0,
            total_process_time=1100,
            eks_nodes_number=eks_nodes_number,
            num_workers=num_workers,
            num_unfinished_tasks = 0,
            code_templates_folder=code_templates_folder
        )


        repeat_number_str = f"Repeat {index}"
        file_name.append(logs_file)
        total_tasks.append(per_dict['total_tasks'])
        average_task_duration.append(per_dict['average_task_duration'])
        min_duration.append(per_dict['min_duration'])
        shortest_task.append(per_dict['shortest_task'])
        longest_task.append(per_dict['longest_task'])
        max_duration.append(per_dict['max_duration'])
        num_error_task.append(per_dict['num_error_task'])
        num_unfinished_tasks.append(per_dict['num_unfinished_tasks'])
        task_duration_in_parallelism.append(per_dict['task_duration_in_parallelism'])
        tasks_durtaion_sum.append(per_dict['tasks_durtaion_sum'])
        # initial_process_time.append(per_dict['initial_process_time'])
        # total_process_time.append(per_dict['total_process_time'])
        effeciencyFactor.append(per_dict['effeciencyFactor'])
        header.append(repeat_number_str)
        index +=1


    if len(average_task_duration) > 1 :
        # Mean and Std
        header.append("Mean")
        header.append("Std")

        mean_of_average_task_duration= statistics.mean(average_task_duration[1:])
        std_of_average_task_duration =  statistics.stdev(average_task_duration[1:])
        average_task_duration.append(mean_of_average_task_duration)
        average_task_duration.append(std_of_average_task_duration)


        mean_of_task_duration_in_parallelism =  statistics.mean(task_duration_in_parallelism[1:])
        std_of_task_duration_in_parallelism =  statistics.stdev(task_duration_in_parallelism[1:])
        task_duration_in_parallelism.append(mean_of_task_duration_in_parallelism)
        task_duration_in_parallelism.append(std_of_task_duration_in_parallelism)



        mean_of_tasks_durtaion_sum =  statistics.mean(tasks_durtaion_sum[1:])
        std_of_tasks_durtaion_sum =  statistics.stdev(tasks_durtaion_sum[1:])
        tasks_durtaion_sum.append(mean_of_tasks_durtaion_sum)
        tasks_durtaion_sum.append(std_of_tasks_durtaion_sum)

        mean_of_init_process_time_list =  statistics.mean(init_process_time_list)
        std_of_init_process_time_list =  statistics.stdev(init_process_time_list)
        initial_process_time = initial_process_time + init_process_time_list
        initial_process_time.append(mean_of_init_process_time_list)
        initial_process_time.append(std_of_init_process_time_list)

        mean_of_total_process_time =  statistics.mean(total_proscee_time_list)
        std_of_total_process_time =  statistics.stdev(total_proscee_time_list)
        total_process_time = total_process_time + total_proscee_time_list
        total_process_time.append(mean_of_total_process_time)
        total_process_time.append(std_of_total_process_time)


        mean_of_effeciencyFactor =  statistics.mean(effeciencyFactor[1:])
        std_of_effeciencyFactor =  statistics.stdev(effeciencyFactor[1:])
        effeciencyFactor.append(mean_of_effeciencyFactor)
        effeciencyFactor.append(std_of_effeciencyFactor)


    performance = [
        header,
        ["Code templates folder", code_templates_folder, ""],
        ["Number of nodes", f"{eks_nodes_number}"],
        ["Number of workers", f"{num_workers}"],
        ["Instance type", f"{instanceType}"],
        file_name,
        average_task_duration,
        min_duration,
        shortest_task,
        max_duration,
        longest_task,
        num_error_task,
        num_unfinished_tasks,
        task_duration_in_parallelism,
        tasks_durtaion_sum,
        initial_process_time,
        total_process_time,
        effeciencyFactor

        ]
    table1 = AsciiTable(performance)
    print(table1.table)
    print("---------")
    print(save_file_path_name)
    with open(save_file_path_name, "w") as file:
        print(table1.table, file=file)
        file.close()
    return 

# def analyze_local_logs_files(
#     logs_file_path_name: str = None,
#     instanceType: str = None,
#     initial_process_time: float = 0,
#     total_process_time: float = 0,
#     eks_nodes_number: int = 0,
#     num_workers: int = 0,
#     save_file_path_name: str = "results/performance.txt",
#     num_unfinished_tasks: int = 0,
#     code_templates_folder: str = None,
# ) -> List[str]:

#     if exists(logs_file_path_name) is False:
#         logger.error(f"{logs_file_path_name} does not exist")
#         return

#     df = pd.read_csv(logs_file_path_name)
    
#     # print(df[(df["host_ip"] == "192.168.7.249")])
#     # print(df.head())
#     # get error task

#     error_task = df[(df["alert_type"] == "SYSTEM_ERROR")]
#     num_error_task = len(error_task)
    
#     worker_dict = process_df_for_gantt(df)
#     shortest_task = ""
#     longest_task = ""
#     min_duration = float("inf")
#     max_duration = 0
#     tasks_durtaion_sum = 0
#     average_task_duration = 0
#     total_tasks = 0
#     min_start = float("inf")
#     max_end = 0
#     duration = 0
#     task_duration_in_parallelism = 0
#     efficiency = 0
#     for key, value in worker_dict.items():
#         # logger.info(f"ip {value['host_ip']} ")
#         # logger.info(f"ip {value} ")
#         if ("start" in value) is False:
#             logger.warning(f"missing 'start' key in task {key}")
#             continue
#         if ("end" in value) is False:
#             logger.warning(f"missing 'end' key in task {key}")
#             continue
#         start = float(value["start"])
#         end = float(value["end"])
#         duration = value["duration"]
#         task = value["task"]
#         if task == "loop_tasks_status_task":
#             continue
#         tasks_durtaion_sum += duration
#         if start < min_start:
#             min_start = start
#         if end > max_end:
#             max_end = end

#         if duration < min_duration:
#             min_duration = duration
#             shortest_task = task
#         if duration > max_duration:
#             max_duration = duration
#             longest_task = task
#         total_tasks += 1
#     task_duration_in_parallelism = max_end - min_start
#     if total_tasks > 0:
#         average_task_duration = tasks_durtaion_sum / total_tasks
#     else:
#         average_task_duration = tasks_durtaion_sum

#     if task_duration_in_parallelism > 0:
#         efficiency = int(
#             (
#                 (tasks_durtaion_sum - task_duration_in_parallelism)
#                 / task_duration_in_parallelism
#             )
#             * 100
#         )

#     ip_accumulation_druations = dict()
#     # --------------------------
#     # calcuate effeciency factor
#     # --------------------------
#     # step 1 , accumulate the process time of each host_ip/pid
#     for key, value in worker_dict.items():
#         _duration = float(value["duration"])
#         _host_ip = value['host_ip']
#         _pid = value['pid']
#         key = str(_host_ip) + "/" +str(_pid)
#         if  key in ip_accumulation_druations:
#             ip_accumulation_druations[key] += _duration
#         else:
#             ip_accumulation_druations[key] =  _duration


#     # step 2 ,divide the total_process_time of each  host_ip/pid with task_duration_in_parallelism
#     # ( total_process_time ) / (task_duration_in_parallelism * number_host_ip_pid)
#     accumulated_process_duration = 0
#     for key , value in ip_accumulation_druations.items():
#         accumulated_process_duration += value
#     effeciency_of_each_ip_pid = dict()
#     effeciencyFactory = 0 
#     if task_duration_in_parallelism > 0 :

#         for key , value in ip_accumulation_druations.items():
#             effeciency_of_each_ip_pid[key] = value/task_duration_in_parallelism

#     if len(ip_accumulation_druations)> 0 :
#         effeciencyFactory = accumulated_process_duration/(task_duration_in_parallelism * len(ip_accumulation_druations))

#         # logger.info(f"ip {value['host_ip']}, start: {start}, end: {end} ")
#     # --------------------------
#     # calcuate effeciency factor
#     # -------------------------- 


#     performance = [
#         ["Performance", "Results", "Info"],
#         ["Code templates folder", code_templates_folder, ""],
#         ["Total tasks", total_tasks, ""],
#         ["Average task duration", f"{average_task_duration} sec"],
#         ["Min task duration", f"{min_duration} sec", shortest_task],
#         ["Max task duration", f"{max_duration} sec", longest_task],
#         ["Number of error tasks", f"{num_error_task}"],
#         ["Number of unfinished tasks", f"{num_unfinished_tasks}"],
#         [
#             "Process tasks duration(in parallel)",
#             f"{task_duration_in_parallelism} sec",
#             "Real data",
#         ],
#         [
#             "Process tasks duration(in serial)",
#             f"{tasks_durtaion_sum} sec",
#             "Estimation",
#         ],
#         ["Efficiency improvement", f"{efficiency} %"],
#         ["Initialize services duration", f"{initial_process_time} sec"],
#         ["Total process durations", f"{total_process_time} sec"],
#         ["Number of nodes", f"{eks_nodes_number}"],
#         ["Number of workers", f"{num_workers}"],
#         ["Instance type", f"{instanceType}"],
#         ["Total efficiency factor", f"{effeciencyFactory} %"],
#     ]
    
    

#     table1 = AsciiTable(performance)
#     print(table1.table)
#     effeciency_factory_list = []
#     print("Individual effeciency factor:")
#     for key, value in effeciency_of_each_ip_pid.items():
#         _temp_array = [str(key), f"{value} %"]
#         print(_temp_array)
#         effeciency_factory_list.append(_temp_array)
#     with open(save_file_path_name, "w") as file:
#         print(table1.table, file=file)
#         file.close()
