
import boto3
from flask import current_app
import os
def connect_aws_client(client_name:str):
    AWS_ACCESS_KEY_ID = current_app.config["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = current_app.config["AWS_SECRET_ACCESS_KEY"]
    AWS_DEFAULT_REGION = current_app.config["AWS_DEFAULT_REGION"]
    if check_aws_validity(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY) :
        client = boto3.client(
            client_name,
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key= AWS_SECRET_ACCESS_KEY
        )
        return client
    raise Exception('AWS Validation Error')
    
def connect_aws_resource(resource_name:str):
    AWS_ACCESS_KEY_ID = current_app.config["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = current_app.config["AWS_SECRET_ACCESS_KEY"]
    AWS_DEFAULT_REGION = current_app.config["AWS_DEFAULT_REGION"]
    if check_aws_validity(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY) :
        resource = boto3.resource(
            resource_name,
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key= AWS_SECRET_ACCESS_KEY
        )
        return resource
    raise Exception('AWS Validation Error')


def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        response = client.list_buckets()
        return True

    except Exception as e:
        if str(e)!="An error occurred (InvalidAccessKeyId) when calling the ListBuckets operation: The AWS Access Key Id you provided does not exist in our records.":
            return True
        raise e

