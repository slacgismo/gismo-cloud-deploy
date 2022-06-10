from ast import Str
from cmath import log
import botocore
from utils.aws_utils import (
    connect_aws_client,
    connect_aws_resource,
    to_s3,
    read_csv_from_s3,
    download_solver_licence_from_s3_and_save,
)
import socket

from project.solardata.solardata_models import SolarData, SolarParams

# from project.solardata.models.SolarParams import SolarParams

import pandas as pd
from os.path import exists

# from project.solardata.models.SolarData import SolarData
from models.WorkerStatus import WorkerStatus

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


def retrive_all_item_from_dyanmodb(
    table_name: str, dynamo_client: "botocore.client.dynamo"
):

    deserializer = TypeDeserializer()
    items = []
    for item in scan_table(dynamo_client, TableName=table_name):
        deserialized_document = {
            k: deserializer.deserialize(v) for k, v in item.items()
        }
        items.append(deserialized_document)
    return items


def scan_table(dynamo_client, *, TableName, **kwargs):

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
            delete_files_from_bucket(bucket_name, file, s3_client)
    except Exception as e:
        print(f"save to s3 error or delete files error ---> {e}")
        raise e


def delete_files_from_bucket(
    bucket_name: str, full_path: str, s3_client: "botocore.client.S3"
) -> None:
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=full_path)
        print(f"Deleted {full_path} success!!")
    except Exception as e:
        print(f"Delete file error ---> {e}")
        raise e


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


def check_solver_licence(
    solarParams: SolarParams = None, s3_client: "botocore.client.S3" = None
) -> None:
    if solarParams.solver_name is None:
        raise Exception("No solver name")

    # check if the file is exist in local directory
    solver_target_file_path = (
        solarParams.solver_saved_lic_file_path
        + "/"
        + solarParams.solver_saved_lic_file_name
    )
    if exists(solver_target_file_path) is False:
        logger.info(
            f"Download MOSEK Licence {solarParams.solver_lic_file_path_name} from {solarParams.solver_lic_bucket}"
        )
        try:
            download_solver_licence_from_s3_and_save(
                s3_client=s3_client,
                bucket_name=solarParams.solver_lic_bucket,
                file_path_name=solarParams.solver_lic_file_path_name,
                saved_file_path=solarParams.solver_saved_lic_file_path,
                saved_file_name=solarParams.solver_saved_lic_file_name,
            )
        except Exception as e:
            raise e


def str_to_bool(s: str):

    if type(s) == type(True):
        return s

    if type(s) != str:
        raise TypeError

    if s == "True":
        return True
    elif s == "False":
        return False
    else:
        raise ValueError


def make_solardata_params_obj_from_json(algorithm_json: str) -> SolarParams:
    try:

        solar_params_json = algorithm_json["solar_data_tools"]

        power_col = str(solar_params_json["power_col"])
        min_val = solar_params_json["min_val"]
        if min_val == "None":
            min_val = None
        else:
            min_val = int(solar_params_json["min_val"])

        max_val = solar_params_json["max_val"]
        if max_val == "None":
            max_val = None
        else:
            max_val = int(solar_params_json["max_val"])

        zero_night = str_to_bool(solar_params_json["zero_night"])
        interp_day = str_to_bool(solar_params_json["interp_day"])
        fix_shifts = str_to_bool(solar_params_json["fix_shifts"])

        density_lower_threshold = float(solar_params_json["density_lower_threshold"])
        density_upper_threshold = float(solar_params_json["density_upper_threshold"])
        linearity_threshold = float(solar_params_json["linearity_threshold"])
        clear_day_smoothness_param = float(
            solar_params_json["clear_day_smoothness_param"]
        )
        clear_day_energy_param = float(solar_params_json["clear_day_energy_param"])
        verbose = str_to_bool(solar_params_json["verbose"])

        start_day_ix = solar_params_json["start_day_ix"]
        if start_day_ix == "None":
            start_day_ix = None
        else:
            start_day_ix = int(solar_params_json["start_day_ix"])

        end_day_ix = solar_params_json["end_day_ix"]
        if end_day_ix == "None":
            end_day_ix = None
        else:
            end_day_ix = int(solar_params_json["end_day_ix"])

        c1 = solar_params_json["c1"]
        if c1 == "None":
            c1 = None
        else:
            c1 = float(solar_params_json["c1"])

        c2 = solar_params_json["c2"]
        if c2 == "None":
            c2 = None
        else:
            c2 = float(solar_params_json["c2"])

        solar_noon_estimator = str(solar_params_json["solar_noon_estimator"])
        correct_tz = str_to_bool(solar_params_json["correct_tz"])
        extra_cols = str(solar_params_json["extra_cols"])

        extra_cols = solar_params_json["extra_cols"]
        if extra_cols == "None":
            extra_cols = None
        else:
            extra_cols = str(solar_params_json["extra_cols"])

        daytime_threshold = float(solar_params_json["daytime_threshold"])
        units = str(solar_params_json["units"])

        solver = solar_params_json["solver"]

        if solver == "None":
            solver = None
        else:
            solver_name = solver["name"]
            solver_lic_bucket = solver["lic_bucket"]
            solver_lic_file_path_name = solver["lic_file_path_name"]
            solver_saved_lic_file_path = solver["lic_saved_target_path"]
            solver_saved_lic_file_name = solver["lic_saved_target_name"]

        solarparams = SolarParams(
            power_col,
            min_val,
            max_val,
            zero_night,
            interp_day,
            fix_shifts,
            density_lower_threshold,
            density_upper_threshold,
            linearity_threshold,
            clear_day_smoothness_param,
            clear_day_energy_param,
            verbose,
            start_day_ix,
            end_day_ix,
            c1,
            c2,
            solar_noon_estimator,
            correct_tz,
            extra_cols,
            daytime_threshold,
            units,
            solver,
            solver_name=solver_name,
            solver_lic_bucket=solver_lic_bucket,
            solver_lic_file_path_name=solver_lic_file_path_name,
            solver_saved_lic_file_path=solver_saved_lic_file_path,
            solver_saved_lic_file_name=solver_saved_lic_file_name,
        )

        return solarparams
    except Exception as e:
        print(f"conver solardata parameter error :{e}")
        raise e


def track_logs(
    task_id: str,
    function_name: str,
    time: str,
    action: str,
    message: str,
    process_file_name: str,
    table_name: str,
    column_name: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
):

    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)
    pid = os.getpid()
    start_status = WorkerStatus(
        host_name=hostname,
        task_id=task_id,
        host_ip=host_ip,
        pid=str(pid),
        function_name=function_name,
        action=action,
        time=time,
        message=message,
        filename=process_file_name,
        column_name=column_name,
    )

    put_item_to_dynamodb(
        table_name=table_name,
        workerstatus=start_status,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
    )


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
