from asyncio.log import logger
from genericpath import exists

import pandas as pd

from typing import List
from modules.utils.eks_utils import match_pod_ip_to_node_name


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


def analyze_local_logs_files(
    logs_file_path_name: str = None,
    instanceType: str = None,
    initial_process_time: float = 0,
    total_process_time: float = 0,
    eks_nodes_number: int = 0,
    num_workers: int = 0,
    save_file_path_name: str = "results/performance.txt",
    num_unfinished_tasks: int = 0,
    code_templates_folder: str = None,
) -> List[str]:

    if exists(logs_file_path_name) is False:
        logger.error(f"{logs_file_path_name} does not exist")
        return

    df = pd.read_csv(logs_file_path_name)
    # print(df[(df["host_ip"] == "192.168.7.249")])
    # print(df.head())
    # get error task

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
        print(value)
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
    effeciencyFactory = 0 
    if task_duration_in_parallelism > 0 :

        for key , value in ip_accumulation_druations.items():
            effeciency_of_each_ip_pid[key] = value/task_duration_in_parallelism

    if len(ip_accumulation_druations)> 0 :
        effeciencyFactory = accumulated_process_duration/(task_duration_in_parallelism * len(ip_accumulation_druations))

        # logger.info(f"ip {value['host_ip']}, start: {start}, end: {end} ")
    # --------------------------
    # calcuate effeciency factor
    # -------------------------- 


    performance = [
        ["Performance", "Results", "Info"],
        ["Code templates folder", code_templates_folder, ""],
        ["Total tasks", total_tasks, ""],
        ["Average task duration", f"{average_task_duration} sec"],
        ["Min task duration", f"{min_duration} sec", shortest_task],
        ["Max task duration", f"{max_duration} sec", longest_task],
        ["Number of error tasks", f"{num_error_task}"],
        ["Number of unfinished tasks", f"{num_unfinished_tasks}"],
        [
            "Process tasks duration(in parallel)",
            f"{task_duration_in_parallelism} sec",
            "Real data",
        ],
        [
            "Process tasks duration(in serial)",
            f"{tasks_durtaion_sum} sec",
            "Estimation",
        ],
        ["Efficiency improvement", f"{efficiency} %"],
        ["Initialize services duration", f"{initial_process_time} sec"],
        ["Total process durations", f"{total_process_time} sec"],
        ["Number of nodes", f"{eks_nodes_number}"],
        ["Number of workers", f"{num_workers}"],
        ["Instance type", f"{instanceType}"],
        ["Total efficiency factor", f"{effeciencyFactory} %"],
    ]
    
    

    table1 = AsciiTable(performance)
    print(table1.table)
    effeciency_factory_list = []
    print("Individual effeciency factor:")
    for key, value in effeciency_of_each_ip_pid.items():
        _temp_array = [str(key), f"{value} %"]
        print(_temp_array)
        effeciency_factory_list.append(_temp_array)
    with open(save_file_path_name, "w") as file:
        print(table1.table, file=file)
        file.close()
