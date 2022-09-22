import datetime
import time
import json
import re

import pandas as pd

import boto3 
import os
from dotenv import load_dotenv
load_dotenv()
# df = pd.read_csv("init_command_logs_644.csv")
# print(df["file_name"])

# import fnmatch
# files =['this.csv','LICENSE.txt', 'lines.txt', 'listwidget.ui', 'lo1.ui', 'lo2.ui', 'lo3.ui', 'logo.png', 'logo.svg', 'lw.ui']
# matching = fnmatch.fnmatch('htis.csv', '*.csv')
# print(matching)
# txt = "Power(W)"
# x = re.search("(W)$", txt)
# if (x):
#     print("Match")


AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

def connect_aws_client(client_name: str, key_id: str, secret: str, region: str):
    try:
        client = boto3.client(
            client_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        return client
    except Exception as e:
        raise e
        

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


def find_matched_column_name_set(
    columns_key: str,
    bucket_name: str,
    file_path_name: str,
    s3_client: "botocore.client.S3",
) :
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
        # logger.error(f"read column from s3 failed :{e}")
        raise e
    matched_column_set = set()
    # print(total_columns)

    for column in total_columns:
        
        match = re.search(columns_key, column)
        print(match,columns_key,column)
        if (match):
            print("match")
            matched_column_set.add(column)
        # for key in columns_key:
            # if key in column:
                
    return matched_column_set



# s3_clinet = connect_aws_client(
#     's3',
#     key_id= AWS_ACCESS_KEY_ID,
#     secret=AWS_SECRET_ACCESS_KEY,
#     region=AWS_DEFAULT_REGION
# )
# match_set= find_matched_column_name_set(
#     columns_key="^Pow",
#     bucket_name='pv.insight.nrel',
#     file_path_name='PVO/PVOutput/46851.csv',
#     s3_client=s3_clinet
# )

# print(match_set)

is_csv = re.search('.csv', 'PVO/PVOutput/46851.csv')
if not is_csv:
    print("not match")
else:
    print("match")
print(is_csv)