import os
import boto3
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION')



def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        response = client.list_buckets()
        return True

    except Exception as e:
        if str(e)!="An error occurred (InvalidAccessKeyId) when calling the ListBuckets operation: The AWS Access Key Id you provided does not exist in our records.":
            return True
        return False


def connect_aws_client(client_name):

    if check_aws_validity(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY) :
        client = boto3.client(
            client_name,
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key= AWS_SECRET_ACCESS_KEY
        )
        return client
    raise Exception('AWS Validation Error')

def connect_aws_resource(resource_name):
    if check_aws_validity(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY) :
        resource = boto3.resource(
            resource_name,
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key= AWS_SECRET_ACCESS_KEY
        )
        return resource
    raise Exception('AWS Validation Error')
    
def check_environment_is_aws():
    my_user = os.environ.get("USER")
    is_aws = True if "ec2" in my_user else False
    return is_aws

def read_all_csv_from_s3_and_parse_dates_from(
    bucket_name:str=None,
    file_path_name:str=None,
    s3_client = None,
    dates_column_name = None,
    index_col=0
    ):

    if bucket_name is None or file_path_name is None or s3_client is None :
        return
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 200:
            print(f"Successful S3 get_object response. Status - {status}")
            # result_df = pd.read_csv(response.get("Body"),
            #                         index_col=index_col)
            result_df = pd.read_csv(response.get("Body"), index_col=0, parse_dates=[dates_column_name], infer_datetime_format=True)
            result_df[dates_column_name] = pd.to_datetime(result_df[dates_column_name], 
                                    unit='s')
            return result_df
        else:
            print(f"Unsuccessful S3 get_object response. Status - {status}")
       
    except Exception as e:
        print(f"error read  file: {file_path_name} error:{e}")
    

    