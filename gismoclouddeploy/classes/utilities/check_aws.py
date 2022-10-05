from genericpath import exists
import boto3
import botocore
import logging
from mypy_boto3_ec2.client import EC2Client
from mypy_boto3_s3.client import S3Client


def check_aws_validity(key_id: str, secret: str) -> bool:
    try:
        client = boto3.client(
            "s3", aws_access_key_id=key_id, aws_secret_access_key=secret
        )
        client.list_buckets()
        return True

    except Exception as e:
        return False


def check_environment_is_aws() -> bool:
    """
    Check current environment is AWS os LOCAL

    Returns
    -------
    :return bool: If it's running on AWS return True, else return False
    """
    datasource_file = "/var/lib/cloud/instance/datasource"
    if exists(datasource_file):
        return True
    else:
        return False


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


def connect_aws_resource(resource_name: str, key_id: str, secret: str, region: str):
    try:
        resource = boto3.resource(
            resource_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        return resource
    except Exception:
        raise Exception("AWS Validation Error")
