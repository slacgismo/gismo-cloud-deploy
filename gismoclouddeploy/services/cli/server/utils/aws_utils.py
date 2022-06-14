import boto3
import pandas as pd
import botocore
import os
import os.path
from typing import List
from mypy_boto3_s3 import S3Client
import os
from io import StringIO

from boto3.dynamodb.types import TypeDeserializer


def check_aws_validity(key_id: str, secret: str) -> bool:
    try:
        client = boto3.client(
            "s3", aws_access_key_id=key_id, aws_secret_access_key=secret
        )
        client.list_buckets()
        return True

    except Exception as e:
        return False


def connect_aws_client(client_name: str, key_id: str, secret: str, region: str):
    try:
        if check_aws_validity(key_id, secret):
            client = boto3.client(
                client_name,
                region_name=region,
                aws_access_key_id=key_id,
                aws_secret_access_key=secret,
            )
            return client
    except Exception:
        raise Exception("AWS Validation Error")


def connect_aws_resource(resource_name: str, key_id: str, secret: str, region: str):
    try:
        if check_aws_validity(key_id, secret):
            resource = boto3.resource(
                resource_name,
                region_name=region,
                aws_access_key_id=key_id,
                aws_secret_access_key=secret,
            )
            return resource
    except Exception:
        raise Exception("AWS Validation Error")


def to_s3(
    bucket: str,
    file_path: str,
    filename: str,
    content,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> None:
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    k = file_path + "/" + filename
    s3_client.put_object(Bucket=bucket, Key=k, Body=content)


def read_column_from_csv_from_s3(
    bucket_name: str = None, file_path_name: str = None, s3_client: str = None
) -> pd.DataFrame:
    if bucket_name is None or file_path_name is None or s3_client is None:
        return

    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        result_df = pd.read_csv(response.get("Body"), nrows=1)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df


def read_csv_from_s3_with_column_name(
    bucket_name: str = None,
    file_path_name: str = None,
    column_name: str = None,
    s3_client: str = None,
) -> pd.DataFrame:

    if (
        bucket_name is None
        or file_path_name is None
        or s3_client is None
        or column_name is None
    ):
        return

    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        result_df = pd.read_csv(
            response.get("Body"),
            index_col=False,
            usecols=[column_name],
        )
        # drop nan
        df = result_df.dropna()
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return df


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
        result_df["timestamp"] = pd.to_datetime(result_df["timestamp"], unit="s")

    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df


def read_csv_from_s3_with_column_and_time(
    bucket_name: str = None,
    file_path_name: str = None,
    column_name: str = None,
    s3_client: "botocore.client.S3" = None,
    index_col: int = 0,
    parse_dates=[0],
) -> pd.DataFrame:
    """
    Read csv file from s3 bucket
    :param : bucket_name
    :param : file_path_name
    :param : column_name
    :param : s3_client , botocore.client.S3
    :param : index_col, column of index
    :param : parse_dates, column of time
    :return: dataframe.
    """

    if (
        bucket_name is None
        or file_path_name is None
        or s3_client is None
        or column_name is None
    ):
        return

    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        # print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(
            response.get("Body"),
            index_col=index_col,
            parse_dates=parse_dates,
            usecols=["Time", column_name],
        )
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df


def read_csv_from_s3(
    bucket_name: str = None, full_path: str = None, s3_client: str = None
) -> pd.DataFrame:
    if bucket_name is None or full_path is None or s3_client is None:
        return

    response = s3_client.get_object(Bucket=bucket_name, Key=full_path)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        result_df = pd.read_csv(response.get("Body"), nrows=1)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df


def download_solver_licence_from_s3_and_save(
    s3_client,
    bucket_name: str,
    file_path_name: str,
    saved_file_path: str,
    saved_file_name: str,
) -> None:

    if not os.path.exists(saved_file_path):
        os.makedirs(saved_file_path)

    saved_file_path_name = saved_file_path + "/" + saved_file_name

    try:
        s3_client.download_file(bucket_name, file_path_name, saved_file_path_name)
    except Exception as e:
        raise e


def list_files_in_bucket(bucket_name: str, s3_client: S3Client):
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


def check_environment_is_aws() -> bool:
    my_user = os.environ.get("USER")
    is_aws = True if "ec2" in my_user else False
    return is_aws


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
    except Exception as e:
        raise f"no logs.csv file :{e}"

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
        print("remove all items from dynamodb completed")
    except Exception as e:
        raise e


def check_ecr_tag_exists(
    image_tag: str = None, repoNme: str = None, ecr_client=None
) -> bool:
    try:
        response = ecr_client.describe_images(
            repositoryName=f"worker", filter={"tagStatus": "TAGGED"}
        )
        for i in response["imageDetails"]:
            if image_tag in i["imageTags"]:
                return True
        return False
    except Exception as e:
        return False
