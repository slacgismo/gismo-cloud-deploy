from re import S
import boto3
from flask import current_app
import os
import pandas as pd


def check_aws_validity(key_id, secret):
    try:
        client = boto3.client(
            "s3", aws_access_key_id=key_id, aws_secret_access_key=secret
        )
        response = client.list_buckets()
        return True

    except Exception as e:
        if (
            str(e)
            != "An error occurred (InvalidAccessKeyId) when calling the ListBuckets operation: The AWS Access Key Id you provided does not exist in our records."
        ):
            return True
        return False


def connect_aws_client(client_name, key_id, secret, region):

    if check_aws_validity(key_id, secret):
        client = boto3.client(
            client_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        return client
    raise Exception("AWS Validation Error")


def connect_aws_resource(resource_name, key_id, secret, region):
    if check_aws_validity(key_id, secret):
        resource = boto3.resource(
            resource_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        return resource
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


def read_column_from_csv_from_s3(bucket_name=None, file_path_name=None, s3_client=None):
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
):

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
            index_col=False,
            # parse_dates=parse_dates,
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
):

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
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        result_df = pd.read_csv(
            response.get("Body"),
            index_col=0,
            parse_dates=["timestamp"],
            infer_datetime_format=True,
        )
        result_df["timestamp"] = pd.to_datetime(result_df["timestamp"], unit="s")
        print(f"result df ---> {result_df}")
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
):
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


def read_all_csv_from_s3(
    bucket_name: str = None,
    file_path_name: str = None,
    s3_client: "botocore.client.S3" = None,
    index_col: int = 0,
):

    if bucket_name is None or file_path_name is None or s3_client is None:
        return
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)
    except Exception as e:
        print(f"error read  file: {file_path_name} error:{e}")
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        # print(f"Successful S3 get_object response. Status - {status}")
        # result_df = pd.read_csv(response.get("Body"),
        #                         index_col=index_col)
        result_df = pd.read_csv(
            response.get("Body"), index_col=0, infer_datetime_format=True
        )
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df


def read_csv_from_s3(
    bucket_name: str = None, full_path: str = None, s3_client: str = None
):
    if bucket_name is None or full_path is None or s3_client is None:
        return

    response = s3_client.get_object(Bucket=bucket_name, Key=full_path)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        # print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(response.get("Body"), nrows=1)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df
