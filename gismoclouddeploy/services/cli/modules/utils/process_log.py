from asyncio.log import logger
from cmath import log
import sys
from numpy import number
import pandas as pd

from typing import List
from modules.utils.eks_utils import match_pod_ip_to_node_name
from server.utils.aws_utils import read_all_csv_from_s3_and_parse_dates_from
from server.models.LogsInfo import LogsInfo
import datetime
from server import models
from terminaltables import AsciiTable
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import plotly.express as px
import plotly.io as pio

import botocore


def process_df_for_gantt_separate_worker(df: pd):
    LogsInfo_list = models.make_logsinfo_object_from_dataframe(df)

    # process timestamp into linear
    # find min
    # combine task from
    worker_dict = {}
    key_start = "start"
    key_end = "end"
    key_task = "task"
    for worker in LogsInfo_list:
        host_ip = worker.host_ip
        task_id = worker.task_id
        if host_ip in worker_dict:

            if task_id in worker_dict[host_ip]:
                # print(f"exit {task_id} in {host_ip}")
                if key_start in worker_dict[host_ip][task_id]:
                    worker_dict[host_ip][task_id][key_end] = worker.time
                else:
                    worker_dict[host_ip][task_id][key_start] = worker.time
                # get duration from datetime
                end = pd.to_datetime(worker_dict[host_ip][task_id][key_end])
                start = pd.to_datetime(worker_dict[host_ip][task_id][key_start])
                worker_dict[host_ip][task_id]["duration"] = int(
                    round((end - start).total_seconds())
                )

            else:
                # print(f"add new task {task_id}")
                temp_dict = {}
                worker_dict[host_ip][task_id] = {}
                if pd.isnull(worker.filename):
                    temp_dict[key_task] = worker.function_name
                else:
                    temp_dict[key_task] = worker.filename

                if worker.action == models.ActionState.ACTION_STOP.name:
                    temp_dict[key_end] = worker.time
                else:
                    temp_dict[key_start] = worker.time
                worker_dict[host_ip][task_id] = temp_dict

        else:
            info_dict = {}
            worker_dict[host_ip] = {}
            if pd.isnull(worker.filename):
                info_dict[key_task] = worker.function_name
            else:
                info_dict[key_task] = worker.filename
            if worker.action == models.ActionState.ACTION_STOP.name:
                info_dict[key_end] = worker.time
            else:
                info_dict[key_start] = worker.time

            worker_dict[host_ip][task_id] = info_dict


def process_logs_subplot():
    print("process_logs")
    df = pd.read_csv(
        "logs.csv", index_col=0, parse_dates=["timestamp"], infer_datetime_format=True
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

    worker_dict = process_df_for_gantt_separate_worker(df)

    # # # Show dataframe
    figures = []
    subplot_titles = []
    for key, value in worker_dict.items():
        gantt_list = []
        subplot_titles.append(key)
        for k2, v2 in value.items():
            item = dict(
                Task=v2["task"],
                Start=(v2["start"]),
                Finish=(v2["end"]),
                Resource=f"{v2['task']}:{v2['duration']}s",
                Duration=v2["duration"],
            )
            gantt_list.append(item)
        gantt_df = pd.DataFrame(gantt_list)

        fgg = ff.create_gantt(
            gantt_df, reverse_colors=True, show_colorbar=True, index_col="Resource"
        )
        figures.append(fgg)

    figs = make_subplots(
        rows=len(figures), cols=1, shared_xaxes=True, subplot_titles=subplot_titles
    )
    row = 1
    for fgg in figures:
        figs["layout"][f"yaxis{row}"].update(fgg.layout.yaxis)
        for trace in fgg.data:
            figs.add_trace(trace, row=row, col=1)
        row += 1
    figs.update_layout(xaxis=dict(tickmode="linear", tick0=0.5, dtick=2))
    figs.show()


def process_df_for_gantt(df: pd):
    LogsInfo_list = models.make_logsinfo_object_from_dataframe(df)

    # process timestamp into linear
    # find min
    # combine task from
    worker_dict = {}
    key_start = "start"
    key_end = "end"
    key_task = "task"
    key_host_ip = "host_ip"
    key_pid = "pid"
    for worker in LogsInfo_list:
        # print(worker.task_id)

        task_id = worker.task_id
        if task_id == "3820789a-40a4-42cb-8bc4-38a02c9b9479":
            print(worker.action)
            print(worker.filename)
        if task_id in worker_dict:
            if key_start in worker_dict[task_id]:
                worker_dict[task_id][key_end] = worker.time
            else:
                worker_dict[task_id][key_start] = worker.time
            # get duration from datetime
            end = pd.to_datetime(worker_dict[task_id][key_end])
            start = pd.to_datetime(worker_dict[task_id][key_start])
            worker_dict[task_id]["duration"] = (end - start).total_seconds()

        else:
            info_dict = {}
            if worker.function_name != "process_data_task":
                info_dict[key_task] = worker.function_name
            else:
                info_dict[key_task] = worker.filename + "/" + worker.column_name
            info_dict[key_host_ip] = worker.host_ip
            info_dict[key_pid] = worker.pid
            if worker.action == models.ActionState.ACTION_STOP.name:
                info_dict[key_end] = worker.time
            else:
                info_dict[key_start] = worker.time
            worker_dict[worker.task_id] = info_dict

    return worker_dict


def process_logs_from_local():

    print("process_logs")
    df = pd.read_csv(
        "logs.csv", index_col=0, parse_dates=["timestamp"], infer_datetime_format=True
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    # match pod id to node name
    pods_name_prefix_set = ("worker", "webapp")
    pods_info_dict = match_pod_ip_to_node_name(pods_name_prefix_set)
    worker_dict = process_df_for_gantt(df)
    # atlter ip to host name

    # # # # Show dataframe

    gantt_list = []
    for key, value in worker_dict.items():
        # print(f"{value} ")
        # print(f"start :{value['start']} end:{value['end']}")
        pod_ip = value["host_ip"]
        node_name = ""
        # get node name
        if pod_ip in pods_info_dict:
            node_name = pods_info_dict[pod_ip]["NOD_NAME"]

        task = f"{node_name}: {value['host_ip']}: {value['pid']}"
        try:
            label = f"{value['task']}: duration:{value['duration']}s"

            item = dict(
                Task=task,
                Start=(value["start"]),
                Finish=(value["end"]),
                Resource=value["task"],
                Node=node_name,
                Label=label,
                Host=value["host_ip"],
                Duration=value["duration"],
            )
        except Exception:
            logger.info(f"skip task {key}")
            continue
        gantt_list.append(item)
    gantt_df = pd.DataFrame(gantt_list)
    fig = px.timeline(
        gantt_df, x_start="Start", x_end="Finish", y="Task", color="Node", text="Label"
    )
    fig.update_yaxes(
        autorange="reversed"
    )  # otherwise tasks are listed from the bottom up
    fig.show()


def process_logs_from_s3(
    bucket: str = None,
    logs_file_path_name: str = None,
    saved_image_name_local: str = None,
    saved_image_name_aws: str = None,
    s3_client: "botocore.client.S3" = None,
):

    df = read_all_csv_from_s3_and_parse_dates_from(
        bucket_name=bucket,
        file_path_name=logs_file_path_name,
        dates_column_name="timestamp",
        s3_client=s3_client,
    )

    pods_name_prefix_set = ("worker", "webapp")
    pods_info_dict = match_pod_ip_to_node_name(pods_name_prefix_set)
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
            item = dict(
                Task=task,
                Start=(value["start"]),
                Finish=(value["end"]),
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
    fig = px.timeline(
        gantt_df, x_start="Start", x_end="Finish", y="Task", color="Node", text="Label"
    )
    fig.update_yaxes(
        autorange="reversed"
    )  # otherwise tasks are listed from the bottom up

    pio.write_image(
        fig, saved_image_name_local, format="png", scale=1, width=2400, height=1600
    )

    img_data = open(saved_image_name_local, "rb")
    s3_client.put_object(
        Bucket=bucket, Key=saved_image_name_aws, Body=img_data, ContentType="image/png"
    )


def analyze_logs_files(
    bucket: str = None,
    logs_file_path_name: str = None,
    s3_client: "botocore.client.S3" = None,
    initial_process_time: float = 0,
    total_process_time: float = 0,
    eks_nodes_number: int = 0,
    num_workers: int = 0,
    save_file_path_name: str = "results/performance.txt",
) -> List[str]:

    df = read_all_csv_from_s3_and_parse_dates_from(
        bucket_name=bucket,
        file_path_name=logs_file_path_name,
        dates_column_name="timestamp",
        s3_client=s3_client,
    )

    # get error task

    error_task = df[(df["message.Subject.alert_type"] == "SYSTEM_ERROR")]
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
    effeciency = 0
    num_unfinished_task = 0
    for key, value in worker_dict.items():
        if ("start" in value) is False:
            logger.warning(f"missing 'start' key in task {key}")
            continue
        if ("end" in value) is False:
            num_unfinished_task += 1
            continue
        start = float(value["start"].timestamp())
        end = float(value["end"].timestamp())
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
        effeciency = int(
            (
                (tasks_durtaion_sum - task_duration_in_parallelism)
                / task_duration_in_parallelism
            )
            * 100
        )
    performance = [
        ["Performance", "Results", "Info"],
        ["Total tasks", total_tasks, ""],
        ["Average task duration", f"{average_task_duration} sec"],
        ["Min task duration", f"{min_duration} sec", shortest_task],
        ["Max task duration", f"{max_duration} sec", longest_task],
        ["Number of error tasks", f"{num_error_task}"],
        ["Number of unfinished tasks", f"{num_unfinished_task}"],
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
        ["Effeciency improvement", f"{effeciency} %"],
        ["Initialize services duration", f"{initial_process_time} sec"],
        ["Total process durations", f"{total_process_time} sec"],
        ["Number of nodes", f"{eks_nodes_number}"],
        ["Number of workers", f"{num_workers}"],
    ]
    table1 = AsciiTable(performance)
    print(table1.table)
    with open(save_file_path_name, "w") as file:
        print(table1.table, file=file)
        file.close()
