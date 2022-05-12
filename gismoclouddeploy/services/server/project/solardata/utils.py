from fileinput import filename
import re
from tabnanny import verbose
from tkinter import E
from unicodedata import name
import pandas as pd
from project.solardata.models.SolarParams import SolarParams
from project.solardata.models.SolarData import SolarData
from project.solardata.models.WorkerStatus import WorkerStatus
from datetime import datetime
import os
from io import StringIO
import boto3
from flask import current_app
import solardatatools
import time
import socket
from boto3.dynamodb.types import TypeDeserializer
import uuid
def save_logs_from_dynamodb_to_s3(table_name, saved_bucket, saved_file_path, saved_filename):

    # step 1. get all item from dynamodb
    all_items = retrive_all_item_from_dyanmodb(table_name)

    # step 2 . delete data type

    print("------")
    print(all_items)
    df = pd.json_normalize(all_items)
    csv_buffer=StringIO()
    df.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    try:
        to_s3(saved_bucket,saved_file_path,saved_filename, content)
    except Exception as e:
        print(f"ERROR ---> {e}")
        return False
    return True

def retrive_all_item_from_dyanmodb(table_name):
    dynamo_client =  connect_aws_client('dynamodb')
    deserializer = TypeDeserializer()
    items = []
    for item in scan_table(dynamo_client, TableName=table_name):
        deserialized_document = {k: deserializer.deserialize(v) for k, v in item.items()}
        print(deserialized_document)
        items.append(deserialized_document)
    return items

def scan_table(dynamo_client, *, TableName, **kwargs):
    """
    Generates all the items in a DynamoDB table.

    :param dynamo_client: A boto3 client for DynamoDB.
    :param TableName: The name of the table to scan.

    Other keyword arguments will be passed directly to the Scan operation.
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.scan

    """
    paginator = dynamo_client.get_paginator("scan")

    for page in paginator.paginate(TableName=TableName, **kwargs):
        yield from page["Items"]


def remove_all_items_from_dynamodb(table_name):
    dynamodb_resource = connect_aws_resource('dynamodb')
    table = dynamodb_resource.Table(table_name)
    scan = table.scan()
    with table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(
                Key={
                    'host_ip': each['host_ip'],
                    'timestamp':each['timestamp']
                }
            )
    print("remove all items from db completed")

def put_item_to_dynamodb(table_name:str, workerstatus:WorkerStatus):
    dynamodb_resource = connect_aws_resource('dynamodb')
    table = dynamodb_resource.Table(table_name)    
    response = table.put_item(
    Item={
            'host_name': workerstatus.host_name,
            'host_ip': workerstatus.host_ip,
            'task_id': workerstatus.task_id,
            'function_name' : workerstatus.function_name,
            'action' : workerstatus.action,
            'timestamp': workerstatus.time,
            'message': workerstatus.message,
            'filename': workerstatus.filename,
            'column_name':workerstatus.column_name
        }
    )

    return response

# def put_item_to_dynamodb(table_name:str, workerstatus:WorkerStatus):
#     dynamodb_resource = connect_aws_resource('dynamodb')
#     table = dynamodb_resource.Table(table_name)    
#     response = table.put_item(
#     Item={
#             'id':str(uuid.uuid4()),
#             'host_name': workerstatus.host_name,
#             'host_ip': workerstatus.host_ip,
#             'task_id': workerstatus.task_id,
#             'function_name' : workerstatus.function_name,
#             'action' : workerstatus.action,
#             'time': workerstatus.time,
#             'message': workerstatus.message
#         }
#     )

#     return response

# def get_item_from_dynamodb_with_host_name(table_name,host_name):
#     dynamodb_resource = connect_aws_resource('dynamodb')
#     table = dynamodb_resource.Table(table_name)    


#     response = table.get_item(
#     Key={
#             'id': host_name,
#         }
#     )
#     return response

# def create_dynamodb_table(table_name):
#     dynamodb_client = connect_aws_client('dynamodb')
#     ddb_exceptions = dynamodb_client.exceptions
#     try:
#         table = dynamodb_client.create_table(
#             TableName='table_name',
#             KeySchema=[
#                 {
#                     'AttributeName': 'host_name',
#                     'KeyType': 'HASH' # Partition key
#                 }
#             ],
#             AttributeDefinitions=[
#                 {
#                     'AttributeName': 'host_name',
#                     # AttributeType defines the data type. 'S' is string type and 'N' is number type
#                     'AttributeType': 'S' 
#                 }
        
#             ],
#             ProvisionedThroughput={
#                 # ReadCapacityUnits set to 10 strongly consistent reads per second
#                 'ReadCapacityUnits': 10,
#                 'WriteCapacityUnits': 10 # WriteCapacityUnits set to 10 writes per second
#             }
#         )
#         print("Creating table")
#         waiter = dynamodb_client.get_waiter('table_exists')
#         waiter.wait(TableName=table_name)
#         print(f"{table_name} Table created")
    
#     except ddb_exceptions.ResourceInUseException:
#         print("Table exists")

def connect_aws_client(client_name):
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION')
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

def list_all_buckets_in_s3():
    s3_client = connect_aws_client('s3')
    response = s3_client.list_buckets()
    return response

def list_files_in_bucket(bucket_name):
    """ Get filename and size from S3 , remove non csv file """
    s3_client = connect_aws_client('s3')
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

def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        response = client.list_buckets()
        return True

    except Exception as e:
        if str(e)!="An error occurred (InvalidAccessKeyId) when calling the ListBuckets operation: The AWS Access Key Id you provided does not exist in our records.":
            return True
        return False


# def read_column_from_csv_from_s3(
#     bucket_name=None,
#     file_path=None,
#     file_name=None,
#     s3_client = None
#     ):
#     full_path = file_path + "/" + file_name
#     if bucket_name is None or full_path is None or s3_client is None:
#         return
    
#     response = s3_client.get_object(Bucket=bucket_name, Key=full_path)

#     status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

#     if status == 200:
#         print(f"Successful S3 get_object response. Status - {status}")
#         result_df = pd.read_csv(response.get("Body"),nrows =1)
#     else:
#         print(f"Unsuccessful S3 get_object response. Status - {status}")
#     return result_df

def read_csv_from_s3_with_column_and_time(
    bucket_name=None,
    file_path_name=None,
    column_name = None,
    s3_client = None,
    index_col=0,
    parse_dates=[0],
    ):

    if bucket_name is None or file_path_name is None or s3_client is None or column_name is None :
        return
    
    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(response.get("Body"),
                                index_col=index_col,
                                parse_dates=parse_dates,
                                usecols=['Time',column_name])
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df

def read_csv_from_s3_with_column_name(
    bucket_name=None,
    file_path_name=None,
    column_name = None,
    s3_client = None,
    # index_col=0,
    # parse_dates=[0],
    ):

    if bucket_name is None or file_path_name is None or s3_client is None or column_name is None :
        return
    
    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(response.get("Body"),
                                # index_col=index_col,
                                # parse_dates=parse_dates,
                                usecols=[column_name])
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df

def read_csv_from_s3_first_two_rows(
    bucket_name=None,
    file_path_name=None,
    s3_client = None,
    index_col=0,
    parse_dates=[0],
    usecols=[1,3],
    ):

    if bucket_name is None or file_path_name is None or s3_client is None :
        return
    
    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(response.get("Body"),
                                index_col=index_col,
                                parse_dates=parse_dates,
                                usecols=usecols)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df

def read_csv_from_s3_first_three_rows(
    bucket_name=None,
    file_path_name=None,
    s3_client = None,
    index_col=0,
    parse_dates=[0],
    usecols=[1,3],
    ):

    if bucket_name is None or file_path_name is None or s3_client is None :
        return
    
    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(response.get("Body"),
                                index_col=index_col,
                                parse_dates=parse_dates,
                                usecols=usecols)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df

def to_s3(bucket,file_path,filename, content):
    s3_client = connect_aws_client('s3')
    k = file_path+"/"+filename
    s3_client.put_object(Bucket=bucket, Key=k, Body=content)




def process_solardata_tools(  
                            task_id:str = None,
                            bucket_name:str = None,
                            file_path_name:str = None,
                            column_name:str = None,
                            start_time:str = None, 
                            saved_bucket:str = None,
                            saved_file_path:str = None,
                            saved_filename:str = None,
                            solarParams: SolarParams = None
                            ):
    if bucket_name is None or file_path_name is None or column_name is None or saved_bucket is None or solarParams is None:
        return False
    error_message = ""
    s3_client = connect_aws_client("s3")
    try:
        df = read_csv_from_s3_with_column_and_time(bucket_name,file_path_name,column_name,s3_client)
    except Exception as e:
        error_message += f"read column and time error: {e}"
        print(f"read column and time error: {e}")
        return False

    solarParams.power_col = column_name


    try:
        dh = solardatatools.DataHandler(df)
        print(f"run pipeline solarParams.verbose: {solarParams.verbose}, solver: {solarParams.solver}")
        dh.run_pipeline(power_col=column_name,
                        min_val= solarParams.min_val,
                        max_val = solarParams.max_val,
                        zero_night = solarParams.zero_night, 
                        interp_day = solarParams.interp_day,
                        fix_shifts = solarParams.fix_shifts,
                        density_lower_threshold = solarParams.density_lower_threshold,
                        density_upper_threshold = solarParams.density_upper_threshold,
                        linearity_threshold = solarParams.linearity_threshold,
                        clear_day_smoothness_param = solarParams.clear_day_smoothness_param,
                        clear_day_energy_param = solarParams.clear_day_energy_param,
                        verbose = solarParams.verbose,
                        start_day_ix = solarParams.start_day_ix,
                        end_day_ix = solarParams.end_day_ix,
                        c1 = solarParams.c1,
                        c2 = solarParams.c2,
                        solar_noon_estimator = solarParams.solar_noon_estimator,
                        correct_tz = solarParams.correct_tz,
                        extra_cols = solarParams.extra_cols,
                        daytime_threshold = solarParams.daytime_threshold,
                        units = solarParams.units,
                        solver = solarParams.solver
                        )
       
        length=float("{:.2f}".format(dh.num_days))
        print(f"length {length}")
        if dh.num_days >= 365:
            length = float("{:.2f}".format(dh.num_days / 365))

        capacity_estimate = float("{:.2f}".format(dh.capacity_estimate))

        power_units = str(dh.power_units)
        if power_units == "W":
            capacity_estimate =float("{:.2f}".format( dh.capacity_estimate / 1000))
        data_sampling = int(dh.data_sampling)

        if dh.raw_data_matrix.shape[0] >1440:
            data_sampling = int(dh.data_sampling * 60)

        data_quality_score =  float("{:.1f}".format( dh.data_quality_score * 100 ))
        data_clearness_score = float("{:.1f}".format( dh.data_clearness_score * 100 ))
        time_shifts = bool(dh.time_shifts)
        num_clip_points = int( dh.num_clip_points )
        tz_correction = int(dh.tz_correction)
        inverter_clipping = bool(dh.inverter_clipping)
        normal_quality_scores = bool(dh.normal_quality_scores)
        capacity_changes = bool(dh.capacity_changes)
        end_time = time.time() 
        process_time =float(end_time)  - float(start_time)
        end_time_date = datetime.fromtimestamp(end_time)
        start_time_date = datetime.fromtimestamp(start_time)

        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)


        # print(f"file: {file_path_name},column_name:{column_name} , process_time {process_time}, hostname: {hostname}, host_ip: {host_ip}, start_time: {start_time_date}, end_time: {end_time_date}, process_time: {process_time}")
        solarData = SolarData(task_id=task_id,
                            hostname= hostname,
                            host_ip = host_ip,
                            stat_time = start_time_date,
                            end_time = end_time_date,
                            bucket_name=(bucket_name),
                            file_path_name = (file_path_name),
                            column_name=(column_name),
                            process_time=(process_time),
                            length=(length),
                            power_units=(power_units),
                            capacity_estimate=(capacity_estimate),
                            data_sampling=(data_sampling),
                            data_quality_score = (data_quality_score),
                            data_clearness_score = (data_clearness_score),
                            error_message=(error_message),
                            time_shifts=(time_shifts),
                            capacity_changes=(capacity_changes),
                            num_clip_points=(num_clip_points),
                            tz_correction =(tz_correction),
                            inverter_clipping = (inverter_clipping),
                            normal_quality_scores=(normal_quality_scores),
                            )
        print(f"results solarData to json ---> :{solarData.to_json()} ")
        response = save_solardata_to_file(solarData.to_json(),saved_bucket,saved_file_path,saved_filename)
        print(f"------ save solardata to S3 response: {response}")


        return True
       
    except Exception as e:
        error_message += str(e)
        return False
    
    


def save_solardata_to_file(solardata, saved_bucket, saved_file_path, saved_filename):
    print("----------->")
    print(f"save_bucket:{saved_bucket},saved_file_path: {saved_file_path},saved_filename :{saved_filename} ")
    df = pd.json_normalize(solardata)
    csv_buffer=StringIO()
    df.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    try:
        to_s3(saved_bucket,saved_file_path,saved_filename, content)
    except Exception as e:
        print(f"ERROR ---> {e}")
        return False

def combine_files_to_file(bucket_name, source_folder, target_folder, target_filename):
    """ 
    Combine all files in sorce folder and save into target folder and target file.
    After the process is completed, all files in source folder will be deleted.
    """
    print("combine files ---->")
    s3_client = connect_aws_client('s3')
    filter_files = list_files_in_folder_of_bucket(bucket_name,source_folder,s3_client)
 
    if not filter_files:
        print("No tmp file in folder")
        return False
    contents = []
    for file in filter_files:
         df = read_csv_from_s3(bucket_name,file, s3_client)
         contents.append(df)
    frame = pd.concat(contents, axis=0, ignore_index=True) 
    csv_buffer=StringIO()
    frame.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    try:
        to_s3(bucket_name,target_folder,target_filename, content)
        print(f"Save to {target_filename} success!!")
        # delete files 
        for file in filter_files:
           delete_files_from_buckett(bucket_name,file,s3_client)
    except Exception as e:
        print(f"ERROR ---> {e}")
        return False


def delete_files_from_buckett(bucket_name, full_path, s3_client):
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=full_path)
        print(f"Deleted {full_path} success!!")
    except Exception as e:
        print(f"ERROR ---> {e}")
        return False


def list_files_in_folder_of_bucket(bucket_name, file_path, s3_client):
    """ Get filename from a folder of the bucket , remove non csv file """
    
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    files = response['Contents']
    filterFiles =[]
    for file in files:
        split_tup = os.path.splitext(file['Key'])
        path, filename = os.path.split(file['Key'])
        file_extension = split_tup[1]
        if file_extension == ".csv" and path == file_path:
            filterFiles.append(file['Key'])
    return  filterFiles


def read_csv_from_s3(
    bucket_name=None,
    full_path = None,
    s3_client = None
    ):
    if bucket_name is None or full_path is None or s3_client is None:
        return
    
    response = s3_client.get_object(Bucket=bucket_name, Key=full_path)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(response.get("Body"),nrows =1)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df
