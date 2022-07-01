from asyncio.log import logger
from cmath import log
from genericpath import exists

import pandas as pd

from typing import List
from modules.utils.eks_utils import match_pod_ip_to_node_name


# from server.models.LogsInfo import LogsInfo
import datetime
from terminaltables import AsciiTable

import plotly.express as px
import plotly.io as pio
from .modiy_config_parameters import modiy_config_parameters
import botocore
from .check_aws import connect_aws_client


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


# def process_logs_from_local():

#     print("process_logs")
#     df = pd.read_csv(
#         "logs.csv", index_col=0, parse_dates=["timestamp"], infer_datetime_format=True
#     )
#     df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
#     # match pod id to node name
#     pods_name_prefix_set = ("worker", "webapp")
#     pods_info_dict = match_pod_ip_to_node_name(pods_name_prefix_set)
#     worker_dict = process_df_for_gantt(df)
#     # atlter ip to host name

#     # # # # Show dataframe

#     gantt_list = []
#     for key, value in worker_dict.items():
#         pod_ip = value["host_ip"]
#         node_name = ""
#         # get node name
#         if pod_ip in pods_info_dict:
#             node_name = pods_info_dict[pod_ip]["NOD_NAME"]

#         task = f"{node_name}: {value['host_ip']}: {value['pid']}"
#         try:
#             label = f"{value['task']}: duration:{value['duration']}s"

#             item = dict(
#                 Task=task,
#                 Start=(value["start"]),
#                 Finish=(value["end"]),
#                 Resource=value["task"],
#                 Node=node_name,
#                 Label=label,
#                 Host=value["host_ip"],
#                 Duration=value["duration"],
#             )
#         except Exception:
#             logger.info(f"skip task {key}")
#             continue
#         gantt_list.append(item)
#     gantt_df = pd.DataFrame(gantt_list)
#     fig = px.timeline(
#         gantt_df, x_start="Start", x_end="Finish", y="Task", color="Node", text="Label"
#     )
#     fig.update_yaxes(
#         autorange="reversed"
#     )  # otherwise tasks are listed from the bottom up
#     fig.show()


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
    # print(pods_info_dict)
    worker_dict = process_df_for_gantt(df)
    # # # # Show dataframe

    gantt_list = []
    for key, value in worker_dict.items():
        # print(value)
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
) -> List[str]:

    if exists(logs_file_path_name) is False:
        logger.error(f"{logs_file_path_name} does not exist")
        return
    # logger.info("-==============")
    # logger.info(logs_file_path_name)
    df = pd.read_csv(logs_file_path_name)
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
    performance = [
        ["Performance", "Results", "Info"],
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
    ]
    table1 = AsciiTable(performance)
    print(table1.table)
    with open(save_file_path_name, "w") as file:
        print(table1.table, file=file)
        file.close()


# def analyze_logs_files(
#     bucket: str = None,
#     instanceType:str = None,
#     logs_file_path_name: str = None,
#     s3_client: "botocore.client.S3" = None,
#     initial_process_time: float = 0,
#     total_process_time: float = 0,
#     eks_nodes_number: int = 0,
#     num_workers: int = 0,
#     save_file_path_name: str = "results/performance.txt",
# ) -> List[str]:
#     try:
#         df = read_all_csv_from_s3_and_parse_dates_from(
#             bucket_name=bucket,
#             file_path_name=logs_file_path_name,
#             dates_column_name="timestamp",
#             s3_client=s3_client,
#         )
#     except Exception as e:
#         logger.error(f"Read {logs_file_path_name} failed")
#         raise e

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
#     effeciency = 0
#     num_unfinished_task = 0
#     for key, value in worker_dict.items():
#         if ("start" in value) is False:
#             logger.warning(f"missing 'start' key in task {key}")
#             continue
#         if ("end" in value) is False:
#             num_unfinished_task += 1
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
#         effeciency = int(
#             (
#                 (tasks_durtaion_sum - task_duration_in_parallelism)
#                 / task_duration_in_parallelism
#             )
#             * 100
#         )
#     performance = [
#         ["Performance", "Results", "Info"],
#         ["Total tasks", total_tasks, ""],
#         ["Average task duration", f"{average_task_duration} sec"],
#         ["Min task duration", f"{min_duration} sec", shortest_task],
#         ["Max task duration", f"{max_duration} sec", longest_task],
#         ["Number of error tasks", f"{num_error_task}"],
#         ["Number of unfinished tasks", f"{num_unfinished_task}"],
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
#         ["Effeciency improvement", f"{effeciency} %"],
#         ["Initialize services duration", f"{initial_process_time} sec"],
#         ["Total process durations", f"{total_process_time} sec"],
#         ["Number of nodes", f"{eks_nodes_number}"],
#         ["Number of workers", f"{num_workers}"],
#         ["Instance type", f"{instanceType}"]
#     ]
#     table1 = AsciiTable(performance)
#     print(table1.table)
#     with open(save_file_path_name, "w") as file:
#         print(table1.table, file=file)
#         file.close()
