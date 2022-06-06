from asyncio.log import logger
import imp
import os
import boto3
import pandas as pd
from typing import List
from dotenv import load_dotenv
load_dotenv()
# AWS_ACCESS_KEY_ID = os.getenv('aws_access_key')
# AWS_SECRET_ACCESS_KEY = os.getenv('aws_secret_key')
# AWS_DEFAULT_REGION = os.getenv('aws_region')



def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        response = client.list_buckets()
        return True

    except Exception as e:
        if str(e)!="An error occurred (InvalidAccessKeyId) when calling the ListBuckets operation: The AWS Access Key Id you provided does not exist in our records.":
            return True
        return False


def connect_aws_client(client_name,key_id,secret, region):

    if check_aws_validity(key_id,secret) :
        client = boto3.client(
            client_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key= secret
        )
        return client
    raise Exception('AWS Validation Error')

def connect_aws_resource(resource_name,key_id,secret,region):
    if check_aws_validity(key_id,secret) :
        resource = boto3.resource(
            resource_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key= secret
        )
        return resource
    raise Exception('AWS Validation Error')
    
def check_environment_is_aws() -> bool:
    my_user = os.environ.get("USER")
    is_aws = True if "ec2" in my_user else False
    return is_aws

def read_all_csv_from_s3_and_parse_dates_from(
    bucket_name:str=None,
    file_path_name:str=None,
    s3_client:'botocore.client.S3' = None,
    dates_column_name:str = None,
    index_col:int=0
    ):

    if bucket_name is None or file_path_name is None or s3_client is None :
        return
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 200:
            result_df = pd.read_csv(response.get("Body"), index_col=0, parse_dates=[dates_column_name], infer_datetime_format=True)
            result_df[dates_column_name] = pd.to_datetime(result_df[dates_column_name], 
                                    unit='s')
            return result_df
        else:
            print(f"Unsuccessful S3 get_object response. Status - {status}")
       
    except Exception as e:
        print(f"error read  file: {file_path_name} error:{e}")
        raise e

def list_files_in_bucket(bucket_name:str, key_id:str, secret_key:str, aws_region:str) -> List[str]:
    """ Get filename and size from S3 , remove non csv file """
    s3_client = connect_aws_client(client_name='s3', key_id=key_id, secret=secret_key, region=aws_region)
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    files = response['Contents']
    filterFiles =[]
    for file in files:
        split_tup = os.path.splitext(file['Key'])
        file_extension = split_tup[1]
        if file_extension == ".csv":
            obj = {
                'Key': file['Key'],
                'Size': file['Size'],
            }
            filterFiles.append(obj)
    return  filterFiles