
from flask import jsonify
from celery.signals import task_postrun
import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
import os
import boto3
import pandas as pd
import solardatatools
import asyncio
import numbers
from project.solardata.models.SolarData import SolarData 
from project.solardata.models.SolarParams import SolarParams,make_solardata_params_from_str
from project.solardata.models.Configure import Configure
from io import StringIO
import time

logger = get_task_logger(__name__)

@shared_task()
def combine_files_to_file_task(bucket_name,source_folder,target_folder,target_filename):
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import combine_files_to_file
    app = create_app()
    with app.app_context():
        response = combine_files_to_file(bucket_name, source_folder, target_folder, target_filename)
        return response

@shared_task()
def read_all_datas_from_solardata():
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    from project import create_app
    from project.solardata.models import SolarData

    app = create_app()
    with app.app_context():
        solardata = [solardata.to_json()
                     for solardata in SolarData.query.all()]
        return solardata


@shared_task()
def save_data_from_db_to_s3_task(bucket_name, file_path, file_name, delete_data):
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import to_s3
    app = create_app()
    with app.app_context():
        solardatas = [solardata.to_json()
                      for solardata in SolarData.query.all()]
        # logger.info(solardatas)

        # convert josn to csv file and save to s3
        # current_app.logger.info(all_datas)
        df = pd.json_normalize(solardatas)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer)
        content = csv_buffer.getvalue()
        try:
            logger.info(bucket_name, file_path, file_name)
            to_s3(bucket_name, file_path, file_name, content)
        except Exception as e:
            response_object = {
                'status': 'failed',
                'container_id': os.uname()[1],
                'error': str(e)
            }
        return response_object


@shared_task(bind=True)
def process_data_task(self, bucket_name,file_path_name, column_name,saved_bucket, saved_file_path, saved_filename,start_time,solar_params_str:str) -> str:
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    solar_params_obj = make_solardata_params_from_str(solar_params_str)
    print(f"solar_params_obj verbose {solar_params_obj.verbose}")
    # print("hello world here")
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import (
        process_solardata_tools
    )
    app = create_app()
    with app.app_context():
        process_solardata_tools(  
                            self.request.id,
                            bucket_name ,
                            file_path_name,
                            column_name,
                            start_time,
                            saved_bucket,
                            saved_file_path,
                            saved_filename,
                            solar_params_obj
                            )
        print("process solardata")
        # return True

@shared_task()
def loop_tasks_status_task(delay,count,task_ids):
    print(f"--------------> delay: {delay}")
  
    for id in task_ids:
        # print(f"id {id}")
        res = AsyncResult(str(id))
        print(f"---- >   res status {res.status} id:{res.task_id}")
    # while count > 0:
    #     time.sleep(delay)
    #     count -= 1
