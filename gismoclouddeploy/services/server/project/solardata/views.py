import os
import requests
from flask import current_app, render_template, jsonify,current_app,request
from celery.result import AsyncResult
from . import solardata_blueprint
from project.solardata.models import SolarData
import boto3
import time
from project.solardata.tasks import process_data_task
from project import csrf,db

import pandas as pd


@solardata_blueprint.route('/ping/', methods=['GET'])
def ping():
    return jsonify({
        'status': 'success',
        'message': 'pong!',
        'container_id': os.uname()[1]
    })    

    
@solardata_blueprint.route("/run_process_file", methods=["POST"])
@csrf.exempt
def run_process_file():
    request_data = request.get_json()
    bucket_name = request_data['bucket_name']
    file_path = request_data['file_path']
    file_name = request_data['file_name']
    column_name = request_data['column_name']
    solver = request_data['solver']
    start_time = time.time()
    task = process_data_task.apply_async(
        [bucket_name,
        file_path,
        file_name,
        column_name,
        start_time,
        solver])
    # task = process_data_task.apply_async([bucket_name])
    return jsonify({"task_id": task.id}), 202
    # return bucket_name + file_path + file_name + column_name


@solardata_blueprint.route("/tasks/<task_id>", methods=["GET"])
def get_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return jsonify(result), 200

# AWS command
@solardata_blueprint.route("/list_all_buckets_name/", methods=["GET"])

def list_all_buckets_name():
    s3_resource = connect_aws_resource('s3')
    try:
        all_buckets = list_all_buckets_in_s3(s3_resource)
    except Exception as e:
        raise
    return jsonify(all_buckets)


@solardata_blueprint.route("/list_content_of_bucket/", methods=["POST"])
@csrf.exempt
def list_content_of_bucket():

    request_data = request.get_json()
    bucket_name = request_data['bucket_name']
    path = request_data["file_path"]
    s3_resource = connect_aws_resource('s3')
    my_bucket = s3_resource.Bucket(bucket_name)
    all_files = []
    
    for file in  my_bucket.objects.filter(Prefix=path + "/"):
        all_files.append(file.key)
    return jsonify(all_files)

@solardata_blueprint.route("/list_columns_name_of_file/", methods=["POST"])
@csrf.exempt
def list_columns_name_of_file():
    s3_client = connect_aws_client('s3')
    request_data = request.get_json()
    bucket_name = request_data['bucket_name']
    file_path = request_data['file_path']
    file_name = request_data['file_name']
    df = read_column_from_csv_from_s3(bucket_name,file_path,file_name,s3_client)
    column_names = list(df.columns.values)
    print(df.head())
    return jsonify(column_names)

# save results to s3
@solardata_blueprint.route("/save_all_results_from_db_to_s3/", methods=["POST"])
@csrf.exempt
def save_all_results_from_db_to_s3():
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    return response_object


# save results to db
@solardata_blueprint.route("/all_results/", methods=["POST", "GET"])
@csrf.exempt
def all_reuslts():
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    if request.method == 'POST':
        post_data = request.get_json()
        task_id = post_data.get('task_id')
        bucket_name = post_data.get('bucket_name')
        file_path = post_data.get('file_path')
        file_name = post_data.get('file_name')
        column_name = post_data.get('column_name')
        process_time = post_data.get('process_time')

        length = float(post_data.get('length'))
        power_units = post_data.get('power_units')
        capacity_estimate = float(post_data.get('capacity_estimate'))

        data_sampling = int(post_data.get('data_sampling'))
        data_quality_score =float(post_data.get('data_quality_score'))
        data_clearness_score= float(post_data.get('data_clearness_score'))
        error_message = post_data.get('error_message')
        time_shifts = bool(post_data.get('time_shifts'))
        capacity_changes = bool(post_data.get('capacity_changes'))
        num_clip_points = int(post_data.get('num_clip_points'))
        tz_correction = int(post_data.get('tz_correction'))
        inverter_clipping = bool(post_data.get('inverter_clipping'))
        normal_quality_scores = bool(post_data.get('normal_quality_scores'))
        try:
            solardata = SolarData(
                task_id=task_id,
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
            db.session.add(solardata)
            db.session.commit()
            # response_object['message'] = 'Solardata added!'
        except Exception as e:
            db.session.rollback()
            raise
    else:
        response_object['solardata'] = [solardata.to_json() for solardata in SolarData.query.all()]
    return response_object


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
    
def connect_aws_resource(resource_name):
    AWS_ACCESS_KEY_ID = current_app.config["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = current_app.config["AWS_SECRET_ACCESS_KEY"]
    AWS_DEFAULT_REGION = current_app.config["AWS_DEFAULT_REGION"]
    # current_app.logger.info(f'AWS_ACCESS_KEY_ID key {AWS_ACCESS_KEY_ID} {AWS_SECRET_ACCESS_KEY} is persistent now')
    if check_aws_validity(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY) :
        resource = boto3.resource(
            resource_name,
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key= AWS_SECRET_ACCESS_KEY
        )
        return resource
    raise Exception('AWS Validation Error')

def list_all_buckets_in_s3(s3_resource):

    buckets = []
    for bucket in s3_resource.buckets.all():
        buckets.append(bucket.name)
    return buckets

def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        response = client.list_buckets()
        return True

    except Exception as e:
        if str(e)!="An error occurred (InvalidAccessKeyId) when calling the ListBuckets operation: The AWS Access Key Id you provided does not exist in our records.":
            return True
        return False

def list_all_buckets_in_s3(resource):
    buckets = []
    for bucket in resource.buckets.all():
        buckets.append(bucket.name)
    return buckets

def read_column_from_csv_from_s3(
    bucket_name=None,
    file_path=None,
    file_name=None,
    s3_client = None
    ):
    full_path = file_path + "/" + file_name
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