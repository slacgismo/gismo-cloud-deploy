import pandas as pd
from project.solardata.models import SolarData
import os
from io import StringIO
import boto3
from flask import current_app
from project import db
import solardatatools
import time
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

def to_s3(bucket,file_path,filename, content):
    s3_client = connect_aws_client('s3')
    k = file_path+"/"+filename
    s3_client.put_object(Bucket=bucket, Key=k, Body=content)

def transaction_solardata(solardata:SolarData):
    try:
        db.session.add(solardata)
        db.session.commit()
        print("save to postgres success!!!")
    except Exception as e:
        db.session.rollback()
        raise
    return 'done'

def process_solardata_tools(bucket_name,file_path,file_name,column_name,solver,start_time, task_id):

    s3_resource = connect_aws_client("s3")
    df = read_csv_from_s3(bucket_name,file_path,file_name,s3_resource)

    dh = solardatatools.DataHandler(df)
    error_message = ""
    try:
        dh.run_pipeline(power_col=column_name,solver=solver, verbose=False,)
    except Exception as e:
        error_message += str(e)
        return False
    
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
    transaction_solardata(solardata)
    response_object = {
        'status': 'success',
        'solardata': solardata.to_json
    }
    print(response_object)
    return True