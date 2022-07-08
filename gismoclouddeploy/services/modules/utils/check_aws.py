from genericpath import exists
import boto3
import os


def check_aws_validity(key_id: str, secret: str) -> bool:
    try:
        client = boto3.client(
            "s3", aws_access_key_id=key_id, aws_secret_access_key=secret
        )
        client.list_buckets()
        return True

    except Exception as e:
        return False


# def check_environment_is_aws() -> bool:
#     my_user = os.environ.get("USER")
#     is_aws = True if "ec2" in my_user else False
#     return is_aws
def check_environment_is_aws() -> bool:
    datasource_file = "/var/lib/cloud/instance/datasource"
    if exists(datasource_file):
        return True
    else:
        return False
#     try:
#     with open(datasource_file) as f:
#         line = f.readlines()
#         print("I'm running on EC2!")
#         if "DataSourceEc2Local" in line[0]:
#             print("I'm running on EC2!")
# except FileNotFoundError:
#         print(f"{datasource_file} not found")

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
