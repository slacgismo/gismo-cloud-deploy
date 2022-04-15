import random

from flask import jsonify
from celery.signals import task_postrun
import requests
from celery import shared_task
from celery.utils.log import get_task_logger
import time
import os
import boto3
import pandas as pd
import solardatatools
import asyncio
import numbers
from project.solardata.models import SolarData
from io import StringIO

logger = get_task_logger(__name__)

@shared_task()
def read_all_datas_from_solardata():
    # from project import services, queries
    # from flask import current_ap
    # (app, _, _) = current_ap()
    # with app.ctx():
    #     solardata = queries.get_all_data_from_solardata()
    #     print(solardata)
    # all_datas = [solardata.to_json() for solardata in SolarData.query.all()]
    return "done"

   
@shared_task()
def save_data_from_db_to_s3_task(bucket_name,file_path,file_name, delete_data):
    all_datas = [solardata.to_json() for solardata in SolarData.query.all()]
    # convert josn to csv file and save to s3
    # current_app.logger.info(all_datas)
    df = pd.json_normalize(all_datas)
    csv_buffer=StringIO()
    df.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    try:
        to_s3(bucket_name,file_path,file_name, content)
    except Exception as e:
        response_object = {
            'status': 'failed',
            'container_id': os.uname()[1],
            'error': str(e)
        }
    return response_object

def to_s3(bucket,file_path,filename, content):
    s3_client = connect_aws_client('s3')
    k = file_path+"/"+filename
    s3_client.put_object(Bucket=bucket, Key=k, Body=content)



@shared_task(bind=True)
def process_data_task(self, bucket_name,file_path,file_name,column_name,start_time,solver):
    s3_resource = connect_aws_client("s3")
    df = read_csv_from_s3(bucket_name,file_path,file_name,s3_resource)
    dh = solardatatools.DataHandler(df)
    error_message = ""
    try:
        dh.run_pipeline(power_col=column_name,solver=solver, verbose=False,)
    except Exception as e:
        error_message += str(e)
    
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
        
    process_time = time.time() - float(start_time)
    logger.info(f'process_data_task api call to process time {process_time}')
    response_object = {
        'status': 'success',
        'task_id': self.request.id,
        'container_id': os.uname()[1]
    }
    solardata = SolarData(
                task_id=self.request.id,
                bucket_name=bucket_name,
                file_path=file_path,
                file_name=file_name,
                column_name=column_name,
                process_time=process_time,
                length=length,
                power_units=power_units,
                capacity_estimate=capacity_estimate,
                data_sampling=data_sampling,
                data_quality_score = data_quality_score,
                data_clearness_score = data_clearness_score,
                error_message=error_message,
                time_shifts=time_shifts,
                capacity_changes=capacity_changes,
                num_clip_points=num_clip_points,
                tz_correction =tz_correction,
                inverter_clipping = inverter_clipping,
                normal_quality_scores=normal_quality_scores,
    )
    
    response_object['solardata'] = [solardata.to_json()]
    logger.info(response_object)
    return response_object

def read_csv_from_s3(
    bucket_name=None,
    file_path=None,
    file_name=None,
    s3_resource = None,
    index_col=0,
    parse_dates=[0],
    usecols=[1, 3]
    ):
    full_path = file_path + "/" + file_name
    if bucket_name is None or full_path is None or s3_resource is None:
        logger.info("no bucket name or path, or s3 resource")
        return
    
    response = s3_resource.get_object(Bucket=bucket_name, Key=full_path)

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


#  need change in the future
def connect_aws_client(client_name):
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION')
    # current_app.logger.info(f'AWS_ACCESS_KEY_ID key {AWS_ACCESS_KEY_ID} {AWS_SECRET_ACCESS_KEY} is persistent now')
    if check_aws_validity(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY) :
        client = boto3.client(
            client_name,
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key= AWS_SECRET_ACCESS_KEY
        )
        return client
    raise Exception('AWS Validation Error')

def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        response = client.list_buckets()
        return True

    except Exception as e:
        if str(e)!="An error occurred (InvalidAccessKeyId) when calling the ListBuckets operation: The AWS Access Key Id you provided does not exist in our records.":
            return True
        return False



    