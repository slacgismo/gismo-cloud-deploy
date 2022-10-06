from asyncio.log import logger
from genericpath import exists
import logging
import os
import pandas as pd

from typing import List
from .eks_utils import match_pod_ip_to_node_name
import statistics

import datetime
from terminaltables import AsciiTable

import plotly.express as px
import plotly.io as pio
import botocore
from mypy_boto3_s3.client import S3Client


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
    s3_client: S3Client = None,
) -> bool:
    if exists(logs_file_path_name_local) is False:
        logger.error(f"{logs_file_path_name_local} does not exist")
        return False

    df = pd.read_csv(logs_file_path_name_local)

    pods_name_prefix_set = "worker"
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


def analyze_all_local_logs_files(
    project: str,
    instanceType: str,
    num_namspaces: int,
    init_process_time_list: list,
    total_proscee_time_list: list,
    eks_nodes_number: int,
    num_workers: int,
    logs_file_path: str,
    performance_file_txt: str,
    num_unfinished_tasks: int,
    code_templates_folder: str,
    repeat_number: int,
) -> List[str]:

    logging.info(f"initial_process_time : {init_process_time_list}")

    logs_files_list = []
    for _file in os.listdir(logs_file_path):
        prefix = _file.split("-")[0]
        if prefix == "logs":
            logs_files_list.append(_file)

    header = ["Performance"]
    file_name = ["File name"]
    average_task_duration = ["average_task_duration"]
    min_duration = ["min_duration"]
    max_duration = ["max_duration"]
    num_error_task = ["num_error_task"]
    num_unfinished_tasks = ["num_unfinished_tasks"]
    shortest_task = ["shortest_task"]
    longest_task = ["longest_task"]
    task_duration_in_parallelism = ["task_duration_in_parallelism"]
    tasks_durtaion_sum = ["tasks_durtaion_sum"]
    # initial_process_time = init_process_time_list[repeat_number]
    initial_process_time = ["initial_process_time"]
    total_process_time = ["total_process_time"]
    effeciencyFactor = ["effeciencyFactor"]
    total_tasks = ["total_tasks"]

    index = 0
    performance_dict = {}
    for index, logs_file in enumerate(logs_files_list):
        logger.info(f"Porcess {logs_file}")
        logs_path_name = logs_file_path + "/" + logs_file
        per_dict = analyze_signle_local_logs_file(
            logs_file_path_name=logs_path_name,
            initial_process_time=init_process_time_list[index],
            total_process_time=total_proscee_time_list[index],
            num_unfinished_tasks=num_unfinished_tasks,
        )

        repeat_number_str = f"Repeat {index}"
        file_name.append(logs_file)
        total_tasks.append(per_dict["total_tasks"])
        average_task_duration.append(per_dict["average_task_duration"])
        min_duration.append(per_dict["min_duration"])
        shortest_task.append(per_dict["shortest_task"])
        longest_task.append(per_dict["longest_task"])
        max_duration.append(per_dict["max_duration"])
        num_error_task.append(per_dict["num_error_task"])
        num_unfinished_tasks.append(per_dict["num_unfinished_tasks"])
        task_duration_in_parallelism.append(per_dict["task_duration_in_parallelism"])
        tasks_durtaion_sum.append(per_dict["tasks_durtaion_sum"])
        effeciencyFactor.append(per_dict["effeciencyFactor"])
        header.append(repeat_number_str)
        index += 1
        # save to dict
        performance_dict[logs_file] = {
            "total_tasks": total_tasks,
            "average_task_duration": per_dict["average_task_duration"],
            "min_duration": per_dict["min_duration"],
            "shortest_task": per_dict["shortest_task"],
            "longest_task": per_dict["longest_task"],
            "max_duration": per_dict["max_duration"],
            "num_error_task": per_dict["num_error_task"],
            "num_unfinished_tasks": per_dict["num_unfinished_tasks"],
            "task_duration_in_parallelism": per_dict["task_duration_in_parallelism"],
            "tasks_durtaion_sum": per_dict["task_duration_in_parallelism"],
            "effeciencyFactor": per_dict["effeciencyFactor"],
            "repeat_number_str": repeat_number_str,
        }

    initial_process_time = initial_process_time + init_process_time_list
    total_process_time = total_process_time + total_proscee_time_list

    if repeat_number > 1:
        # Mean and Std

        header.append("Mean")
        header.append("Std")
        # average_task_duration
        mean_of_average_task_duration = round(
            statistics.mean(average_task_duration[1:]), 2
        )
        std_of_average_task_duration = round(
            statistics.stdev(average_task_duration[1:]), 2
        )
        average_task_duration.append(mean_of_average_task_duration)
        average_task_duration.append(std_of_average_task_duration)

        # task_duration_in_parallelism
        mean_of_task_duration_in_parallelism = round(
            statistics.mean(task_duration_in_parallelism[1:]), 2
        )
        std_of_task_duration_in_parallelism = round(
            statistics.stdev(task_duration_in_parallelism[1:]), 2
        )
        task_duration_in_parallelism.append(mean_of_task_duration_in_parallelism)
        task_duration_in_parallelism.append(std_of_task_duration_in_parallelism)

        # tasks_durtaion_sum
        mean_of_tasks_durtaion_sum = round(statistics.mean(tasks_durtaion_sum[1:]), 2)
        std_of_tasks_durtaion_sum = round(statistics.stdev(tasks_durtaion_sum[1:]), 2)
        tasks_durtaion_sum.append(mean_of_tasks_durtaion_sum)
        tasks_durtaion_sum.append(std_of_tasks_durtaion_sum)

        # initial_process_time
        mean_of_init_process_time_list = round(
            statistics.mean(init_process_time_list), 2
        )
        std_of_init_process_time_list = round(
            statistics.stdev(init_process_time_list), 2
        )

        initial_process_time.append(mean_of_init_process_time_list)
        initial_process_time.append(std_of_init_process_time_list)

        # total_process_time
        mean_of_total_process_time = round(statistics.mean(total_proscee_time_list), 2)
        std_of_total_process_time = round(statistics.stdev(total_proscee_time_list), 2)

        total_process_time.append(mean_of_total_process_time)
        total_process_time.append(std_of_total_process_time)

        mean_of_effeciencyFactor = round(statistics.mean(effeciencyFactor[1:]), 2)
        std_of_effeciencyFactor = round(statistics.stdev(effeciencyFactor[1:]), 2)
        effeciencyFactor.append(mean_of_effeciencyFactor)
        effeciencyFactor.append(std_of_effeciencyFactor)
    performance = [
        header,
        ["Project", project, ""],
        ["Total number of nodes", f"{eks_nodes_number}"],
        ["Number of namespaces", f"{num_namspaces}"],
        ["Number of workers per namesapces", f"{num_workers}"],
        ["Instance type", f"{instanceType}"],
        file_name,
        total_tasks,
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
        effeciencyFactor,
    ]
    table1 = AsciiTable(performance)
    print(table1.table)
    print(performance_file_txt)
    with open(performance_file_txt, "w") as file:
        print(table1.table, file=file)
        file.close()
    return


def analyze_signle_local_logs_file(
    logs_file_path_name: str = None,
    initial_process_time: float = 0,
    total_process_time: float = 0,
    num_unfinished_tasks: int = 0,
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
        _host_ip = value["host_ip"]
        _pid = value["pid"]
        key = str(_host_ip) + "/" + str(_pid)
        if key in ip_accumulation_druations:
            ip_accumulation_druations[key] += _duration
        else:
            ip_accumulation_druations[key] = _duration

    accumulated_process_duration = 0
    for key, value in ip_accumulation_druations.items():
        accumulated_process_duration += value
    effeciency_of_each_ip_pid = dict()
    effeciencyFactor = 0
    if task_duration_in_parallelism > 0:

        for key, value in ip_accumulation_druations.items():
            effeciency_of_each_ip_pid[key] = value / task_duration_in_parallelism

    if len(ip_accumulation_druations) > 0:
        effeciencyFactor = accumulated_process_duration / (
            task_duration_in_parallelism * len(ip_accumulation_druations)
        )

    performance_dict = {
        "file": logs_file_path_name,
        "total_tasks": total_tasks,
        "average_task_duration": round(average_task_duration, 2),
        "min_duration": round(min_duration, 2),
        "max_duration": round(max_duration, 2),
        "num_error_task": num_error_task,
        "longest_task": longest_task,
        "shortest_task": shortest_task,
        "num_unfinished_tasks": num_unfinished_tasks,
        "task_duration_in_parallelism": round(task_duration_in_parallelism, 2),
        "tasks_durtaion_sum": round(tasks_durtaion_sum, 2),
        "initial_process_time": round(initial_process_time, 2),
        "total_process_time": round(total_process_time, 2),
        "effeciencyFactor": round(effeciencyFactor, 2),
    }
    return performance_dict
