import os
from io import StringIO
import requests
from flask import current_app, render_template, jsonify,request,flash
from celery.result import AsyncResult
from . import solardata_blueprint
from project.solardata.models import SolarData

import time
# from project.solardata.tasks import process_data_task, save_data_from_db_to_s3_task,read_all_datas_from_solardata
from project.solardata.tasks import (
    read_all_datas_from_solardata,
    save_data_from_db_to_s3_task,
    process_data_task
)
# from project import csrf,db
from project import csrf
import pandas as pd

from project.solardata.utils import (
    connect_aws_client,
    connect_aws_resource,
    list_all_buckets_in_s3,
    read_column_from_csv_from_s3,
    list_files_in_bucket
)





@solardata_blueprint.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        'status': 'success',
        'message': 'pong!',
        'container_id': os.uname()[1]
    })    

@solardata_blueprint.route('/read_datas_from_db', methods=['POST'])
@csrf.exempt
def read_datas_from_db():
    task = read_all_datas_from_solardata.apply_async()
    return jsonify({"task_id": task.id}), 202

@solardata_blueprint.route("/run_process_file", methods=["POST"])
@csrf.exempt
def run_process_file():
    request_data = request.get_json()
    bucket_name = request_data['bucket_name']
    file_path = request_data['file_path']
    file_name = request_data['file_name']
    column_name = request_data['column_name']
    solver = request_data['solver']
    print(f"bucket_name: {bucket_name},file_path: {file_path} file_name: {file_name}, column_name: {column_name}, solver: {solver} " )
    start_time = time.time()
    task = process_data_task.apply_async(
        [bucket_name,
        file_path,
        file_name,
        column_name,
        start_time,
        solver])
    return jsonify({"task_id": task.id}), 202


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
@solardata_blueprint.route("/list_buckets", methods=["GET"])

def list_all_buckets_name():
    try:
        all_buckets = list_all_buckets_in_s3()
    except Exception as e:
        raise
    return jsonify(all_buckets)


@solardata_blueprint.route("/list_files", methods=["POST"])
@csrf.exempt
def list_content_of_bucket():

    request_data = request.get_json()
    bucket_name = request_data['bucket_name']
    try:
        all_files = list_files_in_bucket(bucket_name)
    except Exception as e:
        raise
    return jsonify(all_files)
    # s3_resource = connect_aws_resource('s3')
    # my_bucket = s3_resource.Bucket(bucket_name)
    # all_files = []
    
    # for file in  my_bucket.objects.filter(Prefix=path + "/"):
    #     all_files.append(file.key)
    # return jsonify(all_files)

@solardata_blueprint.route("/list_columns_name_of_file", methods=["POST"])
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
@solardata_blueprint.route("/save_all_results_from_db_to_s3", methods=["POST"])
@csrf.exempt
def save_all_results_from_db_to_s3():
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    post_data = request.get_json()
    bucket_name = post_data.get('bucket_name')
    file_path = post_data.get('file_path')
    file_name = post_data.get('file_name')
    delete_data = post_data.get('delete_data')
    task = save_data_from_db_to_s3_task.apply_async(
        [bucket_name,
        file_path,
        file_name,
        delete_data])
    return jsonify({"task_id": task.id}), 202
    

def to_s3(bucket,file_path,filename, content):
    s3_client = connect_aws_client('s3')
    k = file_path+"/"+filename
    s3_client.put_object(Bucket=bucket, Key=k, Body=content)

# save results to db
@solardata_blueprint.route("/all_results", methods=["POST", "GET"])
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
        response_object['solardata']= [solardata.to_json() for solardata in SolarData.query.all()]
    return response_object




