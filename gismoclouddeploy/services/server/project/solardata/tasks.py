
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
from project.solardata.models.WorkerStatus import WorkerStatus
from io import StringIO
import time
import socket
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
def process_data_task(self,table_name, bucket_name,file_path_name, column_name,saved_bucket, saved_file_path, saved_filename,start_time,solar_params_str:str) -> str:
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    solar_params_obj = make_solardata_params_from_str(solar_params_str)
    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)       

    # print("hello world here")
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import (
        process_solardata_tools,
        put_item_to_dynamodb
    )
    app = create_app()
    with app.app_context():
        start_status = WorkerStatus(host_name=hostname,
                                    task_id=self.request.id, 
                                    host_ip=host_ip, 
                                    function_name="process_data_task",
                                    action="idle-stop/busy-start", 
                                    time=str(time.time()),
                                    message="init process data task",
                                    filename=file_path_name,
                                    column_name = column_name
                                    )
        start_res = put_item_to_dynamodb(table_name, workerstatus=start_status)
        print(f"task start res: {start_res}")
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

        print("end of process solardata")
        end_status = WorkerStatus(host_name=hostname,
                                    task_id=self.request.id, 
                                    host_ip=host_ip, 
                                    function_name="process_data_task",
                                    action="busy-stop/idle-start", 
                                    time=str(time.time()),
                                    message="end process data task",
                                    filename=file_path_name,
                                    column_name = column_name
                                    )
        end_status = put_item_to_dynamodb(table_name, workerstatus=end_status)
        print(f"task e nd res: {end_status}")
        # return True

@shared_task(bind=True)
def loop_tasks_status_task( self,
                            delay,
                            count,
                            task_ids,
                            bucket_name, 
                            source_folder,
                            target_folder,
                            target_filename,
                            table_name,
                            saved_log_file_path,
                            saved_log_file_name
                            ):
    print(f"set delay: {delay}, count : {count}")
    counter = int(count)
    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)   
    start_status = WorkerStatus(host_name=hostname,task_id=self.request.id, host_ip=host_ip, function_name="loop_tasks_status_task", action="idle-stop/busy-start", time=str(time.time()),message="init loop_tasks_status_task")
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import (
        put_item_to_dynamodb
    )
    app = create_app()
    with app.app_context():
        start_res = put_item_to_dynamodb(table_name=table_name, workerstatus= start_status) 
        print(f"task start res: {start_res}")
    while counter > 0:
        # check the task status
        time.sleep(int(delay))
        num_completed_task =0
        for id in task_ids:
            res = AsyncResult(str(id))
            status = str(res.status)
           
            if status != "PENDING":
                print(f"completed schedulers: id: {res.task_id} \n task status: {res.status}")
                num_completed_task += 1
        if num_completed_task == len(task_ids):
            print(f"num_success_task: {num_completed_task}")
            break 
        counter -= 1
        print(f"Time: {time.ctime(time.time())}")
    print("------- start combine files, save logs , clean dynamodb items---------")
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import combine_files_to_file,save_logs_from_dynamodb_to_s3,remove_all_items_from_dynamodb
    app = create_app()
    with app.app_context():
        end_status = WorkerStatus(host_name=hostname,task_id=self.request.id, host_ip=host_ip, function_name="loop_tasks_status_task", action="busy-stop/idle-start", time=str(time.time()),message="end loop_tasks_status_task")
        end_status = put_item_to_dynamodb(table_name=table_name, workerstatus = end_status)
        response = combine_files_to_file(bucket_name, source_folder, target_folder, target_filename)

        save_res = save_logs_from_dynamodb_to_s3(table_name=table_name,
                                        saved_bucket=bucket_name,
                                        saved_file_path=saved_log_file_path,
                                        saved_filename=saved_log_file_name )
        remov_res = remove_all_items_from_dynamodb(table_name)
        print(f"remov_res: {remov_res} save_res: {save_res}, response: {response}")
        return response
    