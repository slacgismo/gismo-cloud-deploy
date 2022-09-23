from asyncio import log
import boto3
import pandas as pd

import os
import os.path


import os


def connect_aws_client(client_name: str, key_id: str, secret: str, region: str):
    try:
        client = boto3.client(
            client_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        return client

    except Exception:
        raise Exception("AWS Validation Error")


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


