from ast import Str
from fileinput import filename
from glob import escape
import re
from tabnanny import verbose
from tkinter import E
from unicodedata import name
import pandas as pd
from project.solardata.models.SolarParams import SolarParams
from project.solardata.models.SolarData import SolarData
from project.solardata.models.WorkerStatus import WorkerStatus, make_worker_object_from_dataframe
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
import logging
import plotly.express as px
import io
import plotly.io as pio
from typing import Set

from project.solardata.models.GanttObject import GanttObject

# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')

def process_df_for_gantt(df:pd)  :
    # result = [f(row[0], ..., row[5]) for row in df[['host_ip','filename','function_name','action','column_name','timestamp']].to_numpy()]
    # print(result)
    workerstatus_list= make_worker_object_from_dataframe(df)

    # process timestamp into linear 
    # find min
    #combine task from
    worker_dict={}
    key_start = 'start'
    key_end = 'end'
    key_task = 'task'
    key_host_ip = 'host_ip'
    key_pid = 'pid'
    for worker in workerstatus_list:
        # print(worker.task_id)
        task_id = worker.task_id
        if task_id in worker_dict:
            if key_start in worker_dict[task_id]:
                worker_dict[task_id][key_end] = worker.time
            else:
                worker_dict[task_id][key_start] = worker.time
            # get duration from datetime
            end = pd.to_datetime( worker_dict[task_id][key_end])
            start= pd.to_datetime( worker_dict[task_id][key_start])
            worker_dict[task_id]['duration'] = int(round((end - start).total_seconds()))
  
            # duration = float(worker_dict[task_id][key_end]) - float(worker_dict[task_id][key_start])
            # worker_dict[task_id]['duration'] = duration
           
        else:
            info_dict = {}
            if pd.isnull(worker.filename):
                info_dict[key_task] = worker.function_name
            else:
                info_dict[key_task] = worker.filename
            # print(info_dict['task'])
            info_dict[key_host_ip] = worker.host_ip
            info_dict[key_pid] = worker.pid
            if worker.action == "busy-stop/idle-start":
                info_dict[key_end] = worker.time
            else:
                info_dict[key_start] = worker.time
            worker_dict[worker.task_id] = info_dict
    
    # for key in worker_dict:
    #     print(f" key --->:{key}")


    return worker_dict

def plot_gantt_chart(bucket,file_path_name,saved_image_name):
    logger.info(f" plot gantt")
    print(f"--->plot process file from {bucket}, {file_path_name} to {saved_image_name} ")
    # read log from csv
    s3_client = connect_aws_client('s3')
    df = read_all_csv_from_s3_and_parse_dates_from(bucket_name=bucket,
                                file_path_name=str(file_path_name), 
                                dates_column_name=['timestamp'],
                                s3_client=s3_client)
    # process time 

    # print(f"df {df.head()}")
    # process log file
    worker_dict = process_df_for_gantt(df)

    # plot df 
    gantt_list = []
    for key , value in worker_dict.items():
        print(f"{value} ")
        print(f"start :{value['start']} end:{value['end']}")
        task = f"{value['host_ip']} : {value['pid']}"
        label = f"{value['task']}: duration:{value['duration']}s"
        item = dict(Task=task, 
        Start=(value['start']), 
        Finish=(value['end']), 
        Resource=value['task'],
        Label=label,
        Host=value['host_ip'], 
        Duration = value['duration'])
        gantt_list.append(item)
    gantt_df = pd.DataFrame(gantt_list)
    
    fig = px.timeline(gantt_df, x_start="Start", x_end="Finish", y="Task",color="Host", text="Label")
    fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up

    image_name ="test.png"
    pio.write_image(fig, image_name, format="png", scale=1, width=2400, height=1600) 

    img_data = open(  image_name, "rb")
    s3_client = connect_aws_client('s3')

    s3_client.put_object(Bucket=bucket, Key=saved_image_name, Body=img_data, 
                                 ContentType="image/png")
    return True
    
def save_logs_from_dynamodb_to_s3(table_name, saved_bucket, saved_file_path, saved_filename):

    # step 1. get all item from dynamodb
    all_items = retrive_all_item_from_dyanmodb(table_name)

    # step 2 . delete data type

    df = pd.json_normalize(all_items)
    csv_buffer=StringIO()
    df.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    try:
        to_s3(saved_bucket,saved_file_path,saved_filename, content)
    except Exception as e:
        print(f"ERROR ---> {e}")
        raise e

def retrive_all_item_from_dyanmodb(table_name):
    dynamo_client =  connect_aws_client('dynamodb')
    deserializer = TypeDeserializer()
    items = []
    for item in scan_table(dynamo_client, TableName=table_name):
        deserialized_document = {k: deserializer.deserialize(v) for k, v in item.items()}
        # print(deserialized_document)
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
    try:
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
    except Exception as e:
        raise e

def put_item_to_dynamodb(table_name:str, workerstatus:WorkerStatus):
    dynamodb_resource = connect_aws_resource('dynamodb')
    table = dynamodb_resource.Table(table_name)    
    response = table.put_item(
    Item={
            'host_name': workerstatus.host_name,
            'host_ip': workerstatus.host_ip,
            'task_id':str(workerstatus.task_id),
            'pid': workerstatus.pid,
            'function_name' : workerstatus.function_name,
            'action' : workerstatus.action,
            'timestamp': workerstatus.time,
            'message': workerstatus.message,
            'filename': workerstatus.filename,
            'column_name':workerstatus.column_name
        }
    )

    return response


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
        raise e


def read_column_from_csv_from_s3(
    bucket_name=None,
    file_path_name=None,
    s3_client = None
    ):
    if bucket_name is None or file_path_name is None or s3_client is None:
        return
    
    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        # print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(response.get("Body"),nrows =1)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df

def read_all_csv_from_s3_and_parse_dates_from(
    bucket_name:str=None,
    file_path_name:str=None,
    s3_client = None,
    dates_column_name = None,
    index_col=0
    ):

    if bucket_name is None or file_path_name is None or s3_client is None or dates_column_name is None :
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
        result_df = pd.read_csv(response.get("Body"), index_col=0, parse_dates=['timestamp'], infer_datetime_format=True)
        result_df['timestamp'] = pd.to_datetime(result_df['timestamp'], 
                                  unit='s')
        print(f"result df ---> {result_df}")
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df

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
    #index_col=0,
    # parse_dates=[0],
    ):

    if bucket_name is None or file_path_name is None or s3_client is None or column_name is None :
        return
    
    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 get_object response. Status - {status}")
        result_df = pd.read_csv(response.get("Body"),
                                index_col=False,
                                # parse_dates=parse_dates,
                                usecols=[column_name])
        # drop nan 
        df  = result_df.dropna()
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return df

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
        # df = read_csv_from_s3_first_three_rows(bucket_name,file_path_name,s3_client)
    except Exception as e:
        error_message += f"read column and time error: {e}"
        logger.error(f"read column and time error: {e}")
        raise e

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
        # logger.info(f"results solarData to json ---> :{solarData.to_json()} ")
        response = save_solardata_to_file(solarData.to_json(),saved_bucket,saved_file_path,saved_filename)
        # logger.info(f" ------ save solardata to S3 response: {response}  ------- ")

    
        return response
       
    except Exception as e:
        error_message += str(e)
        logger.error(f"Run solar data tools error {e}")
        raise e
    
    


def save_solardata_to_file(solardata, saved_bucket, saved_file_path, saved_filename):
   
   
    df = pd.json_normalize(solardata)
    csv_buffer=StringIO()
    df.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    try:
        to_s3(saved_bucket,saved_file_path,saved_filename, content)
        logger.info(f"save_bucket:{saved_bucket},saved_file_path: {saved_file_path},saved_filename :{saved_filename} success")
    except Exception as e:
        print(f"save to s3 error ---> {e}")
        raise e

def combine_files_to_file(bucket_name, source_folder, target_folder, target_filename):
    """ 
    Combine all files in sorce folder and save into target folder and target file.
    After the process is completed, all files in source folder will be deleted.
    """
    print("combine files ---->")
    s3_client = connect_aws_client('s3')
    filter_files = list_files_in_folder_of_bucket(bucket_name,source_folder,s3_client)
 
    if not filter_files:
        logger.warning("No tmp file in folder")
        raise Exception('No tmp file error')
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
        print(f"save to s3 error or delete files error ---> {e}")
        raise e


def delete_files_from_buckett(bucket_name, full_path, s3_client):
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=full_path)
        print(f"Deleted {full_path} success!!")
    except Exception as e:
        print(f"Delete file error ---> {e}")
        raise e


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



def publish_message_sns(message: str, subject:str, topic_arn:str) -> str:

    sns_client = connect_aws_client('sns')
    try:
        message_res = sns_client.publish(
            TopicArn=topic_arn,
            Subject = subject,
            Message=message,
        )
        message_id = message_res['MessageId']
        logger.info(
            f'Message published to topic - {topic_arn} with message Id - {message_id}.'
        )
        return message_id
    except Exception as e:
        logger.error(
            f'publish message fail : {e}'
        )




def read_all_csv_from_s3(
    bucket_name:str=None,
    file_path_name:str=None,
    s3_client = None,
    index_col=0
    ):

    if bucket_name is None or file_path_name is None or s3_client is None  :
        return
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)
    except Exception as e:
        print(f"error read  file: {file_path_name} error:{e}")
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 get_object response. Status - {status}")
        # result_df = pd.read_csv(response.get("Body"),
        #                         index_col=index_col)
        result_df = pd.read_csv(response.get("Body"), index_col=0,  infer_datetime_format=True)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df

def find_matched_column_name_set(columns_key:Str, bucket_name:str, file_path_name:str, s3_client) -> Set[set] :
    '''
    Find the match column name from key word. if matched column has no value inside, it will be skipped.
    If this function find exactly match with key and column name , it return the the match column name in set.
    If no exactly match key was found, it return the partial match key with longest data set.  
    '''
    # all_df = read_all_csv_from_s3(bucket_name=bucket_name, file_path_name=file_path_name, s3_client=s3_client)
    total_columns = read_column_from_csv_from_s3(bucket_name=bucket_name, file_path_name=file_path_name, s3_client=s3_client)
    # total_columns = list(all_df.columns)
    exact_column_set = set()
    # find exactly match 
    for column in total_columns:
        # print(column)
        for key in columns_key:
            if key  ==  column:
                # check 
                exact_column_set.add(column)
    # logger.info(f"find exact match column name {exact_column_set}")
    if len(exact_column_set) > 0 :
        return  exact_column_set
    # find partial 
    # logger.info(f"no exact match column name, use parital match")
    # get the max length fo match key
    matched_column_set = set()
    for column in total_columns:
        for key in columns_key:
            if  key in column:
                matched_column_set.add(column)

    max_count = 0
    key_with_most_data = ""
    for key in matched_column_set:
        # check if column has value. 
        tmp_df = read_csv_from_s3_with_column_name(bucket_name=bucket_name,file_path_name=file_path_name, column_name=key,s3_client=s3_client)
        # print(f"key: {key},---> {len(tmp_df)}")
        if max_count <= len(tmp_df):
            max_count = len(tmp_df)
            key_with_most_data = key

    validated_column_set = set()
    validated_column_set.add(key_with_most_data)
    logger.info(f"find partial match column name {validated_column_set}")
    # print(f"validated set{validated_column_set}")
    return validated_column_set

