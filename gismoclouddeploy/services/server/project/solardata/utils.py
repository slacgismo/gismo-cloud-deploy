from ast import Str

from project.solardata.aws_utils import (
    connect_aws_client,
    connect_aws_resource,
    to_s3,
    read_column_from_csv_from_s3,
    read_csv_from_s3_with_column_name,
    read_all_csv_from_s3_and_parse_dates_from,
    read_csv_from_s3,
)

from project.solardata.models.Configure import Configure

import pandas as pd

from project.solardata.models.SolarData import SolarData
from project.solardata.models.WorkerStatus import (
    WorkerStatus,
    make_worker_object_from_dataframe,
)

import os
from io import StringIO

from boto3.dynamodb.types import TypeDeserializer
from typing import List
import logging
import plotly.express as px

import plotly.io as pio
from typing import Set

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def process_df_for_gantt(df: pd):

    workerstatus_list = make_worker_object_from_dataframe(df)

    # process timestamp into linear
    # find min
    # combine task from
    worker_dict = {}
    key_start = "start"
    key_end = "end"
    key_task = "task"
    key_host_ip = "host_ip"
    key_pid = "pid"
    for worker in workerstatus_list:
        # print(worker.task_id)
        task_id = worker.task_id
        if task_id in worker_dict:
            if key_start in worker_dict[task_id]:
                worker_dict[task_id][key_end] = worker.time
            else:
                worker_dict[task_id][key_start] = worker.time
            # get duration from datetime
            end = pd.to_datetime(worker_dict[task_id][key_end])
            start = pd.to_datetime(worker_dict[task_id][key_start])
            worker_dict[task_id]["duration"] = int(round((end - start).total_seconds()))

        else:
            info_dict = {}
            if pd.isnull(worker.filename):
                info_dict[key_task] = worker.function_name
            else:
                info_dict[key_task] = worker.filename
            # print(info_dict['task'])
            info_dict[key_host_ip] = worker.host_ip
            info_dict[key_pid] = worker.pid
            if worker.action == "busy-stop/idle-start":
                info_dict[key_end] = worker.time
            else:
                info_dict[key_start] = worker.time
            worker_dict[worker.task_id] = info_dict

    return worker_dict


def plot_gantt_chart(bucket, file_path_name, saved_image_name):
    logger.info(
        f"--->plot process file from {bucket}, {file_path_name} to {saved_image_name} "
    )
    # read log from csv
    s3_client = connect_aws_client("s3")
    df = read_all_csv_from_s3_and_parse_dates_from(
        bucket_name=bucket,
        file_path_name=str(file_path_name),
        dates_column_name=["timestamp"],
        s3_client=s3_client,
    )
    # process time

    # process log file
    worker_dict = process_df_for_gantt(df)

    # plot df
    gantt_list = []
    for key, value in worker_dict.items():
        print(f"{value} ")
        print(f"start :{value['start']} end:{value['end']}")
        task = f"{value['host_ip']} : {value['pid']}"
        label = f"{value['task']}: duration:{value['duration']}s"
        item = dict(
            Task=task,
            Start=(value["start"]),
            Finish=(value["end"]),
            Resource=value["task"],
            Label=label,
            Host=value["host_ip"],
            Duration=value["duration"],
        )
        gantt_list.append(item)
    gantt_df = pd.DataFrame(gantt_list)

    fig = px.timeline(
        gantt_df, x_start="Start", x_end="Finish", y="Task", color="Host", text="Label"
    )
    fig.update_yaxes(
        autorange="reversed"
    )  # otherwise tasks are listed from the bottom up

    image_name = "test.png"
    pio.write_image(fig, image_name, format="png", scale=1, width=2400, height=1600)

    img_data = open(image_name, "rb")
    s3_client = connect_aws_client("s3")

    s3_client.put_object(
        Bucket=bucket, Key=saved_image_name, Body=img_data, ContentType="image/png"
    )
    return True


def save_logs_from_dynamodb_to_s3(
    table_name: str,
    saved_bucket: str,
    saved_file_path: str,
    saved_filename: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
):

    # step 1. get all item from dynamodb
    dynamo_client = connect_aws_client(
        client_name="dynamodb",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    all_items = retrive_all_item_from_dyanmodb(
        table_name=table_name, dynamo_client=dynamo_client
    )
    df = pd.json_normalize(all_items)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    # remove preivous logs.csv
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    logs_full_path_name = saved_file_path + "/" + saved_filename
    try:
        s3_client.delete_object(Bucket=saved_bucket, Key=logs_full_path_name)
        logger.info("remove previous logs.csv file")
    except Exception as e:
        logger.info("no logs.csv file")
        raise e

    try:
        to_s3(
            bucket=saved_bucket,
            file_path=saved_file_path,
            filename=saved_filename,
            content=content,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
    except Exception as e:
        logger.error(f"ERROR ---> {e}")
        raise e


def retrive_all_item_from_dyanmodb(table_name: str, dynamo_client):

    deserializer = TypeDeserializer()
    items = []
    for item in scan_table(dynamo_client, TableName=table_name):
        deserialized_document = {
            k: deserializer.deserialize(v) for k, v in item.items()
        }
        # print(deserialized_document)
        items.append(deserialized_document)
    return items


def scan_table(dynamo_client, *, TableName, **kwargs):
    """
    Generates all the items in a DynamoDB table.

    :param dynamo_client: A boto3 client for DynamoDB.
    :param TableName: The name of the table to scan.

    Other keyword arguments will be passed directly to the Scan operation.
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.scan

    """
    paginator = dynamo_client.get_paginator("scan")

    for page in paginator.paginate(TableName=TableName, **kwargs):
        yield from page["Items"]


def remove_all_items_from_dynamodb(
    table_name: str, aws_access_key: str, aws_secret_access_key: str, aws_region: str
):
    try:
        dynamodb_resource = connect_aws_resource(
            resource_name="dynamodb",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
        table = dynamodb_resource.Table(table_name)
        scan = table.scan()
        with table.batch_writer() as batch:
            for each in scan["Items"]:
                batch.delete_item(
                    Key={"host_ip": each["host_ip"], "timestamp": each["timestamp"]}
                )
        print("remove all items from db completed")
    except Exception as e:
        raise e


def put_item_to_dynamodb(
    table_name: str,
    workerstatus: WorkerStatus,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
):
    dynamodb_resource = connect_aws_resource(
        resource_name="dynamodb",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    table = dynamodb_resource.Table(table_name)
    response = table.put_item(
        Item={
            "host_name": workerstatus.host_name,
            "host_ip": workerstatus.host_ip,
            "task_id": str(workerstatus.task_id),
            "pid": workerstatus.pid,
            "function_name": workerstatus.function_name,
            "action": workerstatus.action,
            "timestamp": workerstatus.time,
            "message": workerstatus.message,
            "filename": workerstatus.filename,
            "column_name": workerstatus.column_name,
        }
    )

    return response


def list_files_in_bucket(bucket_name: str, s3_client: "botocore.client.S3"):
    """Get filename and size from S3 , remove non csv file"""
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    files = response["Contents"]
    filterFiles = []
    for file in files:
        split_tup = os.path.splitext(file["Key"])
        file_extension = split_tup[1]
        if file_extension == ".csv":
            obj = {
                "Key": file["Key"],
                "Size": file["Size"],
            }
            filterFiles.append(obj)
    return filterFiles


def save_solardata_to_file(
    solardata: SolarData,
    saved_bucket: str,
    saved_file_path: str,
    saved_filename: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> bool:

    try:
        df = pd.json_normalize(solardata)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer)
        content = csv_buffer.getvalue()
        to_s3(
            bucket=saved_bucket,
            file_path=saved_file_path,
            filename=saved_filename,
            content=content,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )

        logger.info(
            f"save_bucket:{saved_bucket},saved_file_path: {saved_file_path},saved_filename :{saved_filename} success"
        )
        return True
    except Exception as e:
        print(f"save to s3 error ---> {e}")
        raise e


def combine_files_to_file(
    bucket_name: str,
    source_folder: str,
    target_folder: str,
    target_filename: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> None:
    """
    Combine all files in sorce folder and save into target folder and target file.
    After the process is completed, all files in source folder will be deleted.
    """
    print("combine files ---->")
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    filter_files = list_files_in_folder_of_bucket(bucket_name, source_folder, s3_client)

    if not filter_files:
        logger.warning("No tmp file in folder")
        raise Exception("Error: No saved tmp file found ")
    contents = []
    for file in filter_files:
        df = read_csv_from_s3(bucket_name, file, s3_client)
        contents.append(df)
    frame = pd.concat(contents, axis=0, ignore_index=True)
    csv_buffer = StringIO()
    frame.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    try:
        to_s3(
            bucket=bucket_name,
            file_path=target_folder,
            filename=target_filename,
            content=content,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        print(f"Save to {target_filename} success!!")
        # delete files
        for file in filter_files:
            delete_files_from_buckett(bucket_name, file, s3_client)
    except Exception as e:
        print(f"save to s3 error or delete files error ---> {e}")
        raise e


def delete_files_from_buckett(bucket_name, full_path, s3_client):
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=full_path)
        print(f"Deleted {full_path} success!!")
    except Exception as e:
        print(f"Delete file error ---> {e}")
        raise e


def list_files_in_folder_of_bucket(
    bucket_name: str, file_path: str, s3_client: "botocore.client.S3"
) -> List[str]:
    """Get filename from a folder of the bucket , remove non csv file"""

    response = s3_client.list_objects_v2(Bucket=bucket_name)
    files = response["Contents"]
    filterFiles = []
    for file in files:
        split_tup = os.path.splitext(file["Key"])
        path, filename = os.path.split(file["Key"])
        file_extension = split_tup[1]
        if file_extension == ".csv" and path == file_path:
            filterFiles.append(file["Key"])
    return filterFiles


def publish_message_sns(
    message: str,
    subject: str,
    topic_arn: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> str:

    sns_client = connect_aws_client(
        client_name="sns",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    try:
        message_res = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
        message_id = message_res["MessageId"]
        logger.info(
            f"Message published to topic - {topic_arn} with message Id - {message_id}."
        )
        return message_id
    except Exception as e:
        logger.error(f"publish message fail : {e}")


def find_matched_column_name_set(
    columns_key: Str,
    bucket_name: str,
    file_path_name: str,
    s3_client: "botocore.client.S3",
) -> Set[set]:
    """
    Find the match column name from key word. if matched column has no value inside, it will be skipped.
    If this function find exactly match with key and column name , it return the the match column name in set.
    If no exactly match key was found, it return the partial match key with longest data set.
    """
    try:
        total_columns = read_column_from_csv_from_s3(
            bucket_name=bucket_name, file_path_name=file_path_name, s3_client=s3_client
        )
    except Exception as e:
        raise e
    matched_column_set = set()
    for column in total_columns:
        for key in columns_key:
            if key in column:
                matched_column_set.add(column)
    validated_column_set = set()
    for key in matched_column_set:
        # check if column has value.
        try:
            tmp_df = read_csv_from_s3_with_column_name(
                bucket_name=bucket_name,
                file_path_name=file_path_name,
                column_name=key,
                s3_client=s3_client,
            )
        except Exception as e:
            raise e
        if len(tmp_df) == 0:
            logger.info(f" ==== > {key} has no value === ")
            continue
        validated_column_set.add(key)
    return validated_column_set


def get_process_filenamef_base_on_command(
    first_n_files: str, configure_obj: Configure, s3_client: "botocore.client.S3"
) -> List[str]:
    n_files = []
    files_dict = list_files_in_bucket(
        bucket_name=configure_obj.bucket, s3_client=s3_client
    )

    if first_n_files == "None":
        logger.info("Process defined files")
        n_files = configure_obj.files
    else:
        try:
            if int(first_n_files) == 0:
                logger.info(f"Process all files in {configure_obj.bucket}")
                for file in files_dict:
                    n_files.append(file["Key"])
            else:
                logger.info(f"Process first {first_n_files} files")
                for file in files_dict[0:int(first_n_files)]:
                    n_files.append(file["Key"])
        except Exception as e:
            logger.error(f"Input {first_n_files} is not an integer")
            raise e
    return n_files
