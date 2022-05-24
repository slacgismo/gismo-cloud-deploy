
import logging

from project import create_app, ext_celery
from flask.cli import FlaskGroup

import socket
from typing import List
from project.solardata.models.WorkerStatus import WorkerStatus
from project.solardata.models.SolarParams import SolarParams
from project.solardata.models.SolarParams import make_solardata_params_from_str
from project.solardata.models.Configure import Configure
from project.solardata.models.Configure import make_configure_from_str
from project.solardata.utils import (
    list_files_in_bucket,
    connect_aws_client,
    put_item_to_dynamodb,
    find_matched_column_name_set)

import click
import time
import os 
from project.solardata.tasks import (

    process_data_task,
    combine_files_to_file_task,
    loop_tasks_status_task,

)
import uuid

app = create_app()
celery = ext_celery.celery

cli = FlaskGroup(create_app=create_app)

# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')





@cli.command("combine_files")
@click.argument('bucket_name', nargs=1)
@click.argument('source_folder', nargs=1)
@click.argument('target_folder', nargs=1)
@click.argument('target_filename', nargs=1)

def combine_files(bucket_name, source_folder,target_folder,target_filename):
    print(f"bucket_name: {bucket_name} ,source_folder {source_folder} ,target_folder: {target_folder},target_filename: {target_filename}")
    task = combine_files_to_file_task.apply_async(
        [bucket_name,
        source_folder,
        target_folder,
        target_filename
        ])

    print(f"task id : {task.id}")
    
# ***************************        
# Process first n files
# ***************************   
@cli.command("process_first_n_files")
@click.argument('config_params_str', nargs=1)
@click.argument('solardata_params_str', nargs=1)
@click.argument('first_n_files', nargs=1)
def process_first_n_files( config_params_str:str,
                    solardata_params_str:str,
                    first_n_files: str
                    ):
    # track scheduler status start    
    configure_obj = make_configure_from_str(config_params_str)
    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)      
    pid = os.getpid()
    temp_task_id = str(uuid.uuid4())
    start_status = WorkerStatus(host_name=hostname,task_id="process_first_n_files", host_ip=host_ip,pid=pid, function_name="process_first_n_files", action="idle-stop/busy-start", time=str(time.time()),message="init process n files")
    start_res = put_item_to_dynamodb(configure_obj.dynamodb_tablename, workerstatus = start_status)
   
    # print(f"start_res {start_res}")
    #     busy-stop/idle-start
    

    print(f"Process first {first_n_files} files")
    task_ids = []
    files = list_files_in_bucket(configure_obj.bucket)
    n_files = files[0:int(first_n_files)]
    s3_client = connect_aws_client('s3')
    for file in n_files:
         # implement partial match 
        matched_column_set = find_matched_column_name_set(bucket_name=configure_obj.bucket, columns_key=configure_obj.column_names, file_path_name=file['Key'],s3_client=s3_client)
        for column in matched_column_set:
       
            path, filename = os.path.split(file['Key'])
            prefix = path.replace("/", "-")
            temp_saved_filename = f"{prefix}-{filename}"
            start_time = time.time()
    
            task_id = process_data_task.apply_async([
                    configure_obj.dynamodb_tablename,
                    configure_obj.bucket,
                    file['Key'],
                    column,
                    configure_obj.saved_bucket,
                    configure_obj.saved_tmp_path,
                    temp_saved_filename,
                    start_time,
                    solardata_params_str
                    ])
            task_ids.append(str(task_id)) 
    for id in task_ids:
        print(id)
    # # loop the task status in celery task
    loop_task = loop_tasks_status_task.apply_async([configure_obj.interval_of_check_task_status, 
                                                    configure_obj.interval_of_exit_check_status,
                                                    task_ids,
                                                    configure_obj.saved_bucket,
                                                    configure_obj.saved_tmp_path,
                                                    configure_obj.saved_target_path,
                                                    configure_obj.saved_target_filename,
                                                    configure_obj.dynamodb_tablename,
                                                    configure_obj.saved_logs_target_path,
                                                    configure_obj.saved_logs_target_filename
                                                    ])

    print(f"loop task: {loop_task}")
    # for id in task_ids:
    end_hostname = socket.gethostname()
    end_host_ip = socket.gethostbyname(hostname)   
    end_status = WorkerStatus(host_name=end_hostname,task_id="process_first_n_files", host_ip=end_host_ip, pid = pid,function_name="process_first_n_files", action="busy-stop/idle-start", time=str(time.time()),message="end process n files")
    end_res = put_item_to_dynamodb(configure_obj.dynamodb_tablename, workerstatus=end_status)

# ***************************        
# Process defined files from config.yaml
# ***************************   

@cli.command("process_files")
@click.argument('config_params_str', nargs=1)
@click.argument('solardata_params_str', nargs=1)

def process_files( config_params_str:str,
                    solardata_params_str:str,               
                    ):
    # convert command str to json format and pass to object

    # track scheduler status start    
    configure_obj = make_configure_from_str(config_params_str)
    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)      
    pid = os.getpid()
    temp_task_id = str(uuid.uuid4())
    start_status = WorkerStatus(host_name=hostname,task_id="process_files_from_yaml", host_ip=host_ip,pid=pid, function_name="process_files_from_yaml", action="idle-stop/busy-start", time=str(time.time()),message="init process files")
    start_res = put_item_to_dynamodb(configure_obj.dynamodb_tablename, workerstatus = start_status)
   
    # print(f"start_res {start_res}")
    #     busy-stop/idle-start

    task_ids = []
    s3_client = connect_aws_client('s3')
    for file in configure_obj.files:
         # implement partial match 
        matched_column_set = find_matched_column_name_set(bucket_name=configure_obj.bucket, columns_key=configure_obj.column_names, file_path_name=file,s3_client=s3_client)
        for column in matched_column_set:
       
            path, filename = os.path.split(file)
            prefix = path.replace("/", "-")
            temp_saved_filename = f"{prefix}-{filename}"
            start_time = time.time()
    
            task_id = process_data_task.apply_async([
                    configure_obj.dynamodb_tablename,
                    configure_obj.bucket,
                    file,
                    column,
                    configure_obj.saved_bucket,
                    configure_obj.saved_tmp_path,
                    temp_saved_filename,
                    start_time,
                    solardata_params_str
                    ])
            task_ids.append(str(task_id)) 
    for id in task_ids:
        print(id)
    # # loop the task status in celery task
    loop_task = loop_tasks_status_task.apply_async([configure_obj.interval_of_check_task_status, 
                                                    configure_obj.interval_of_exit_check_status,
                                                    task_ids,
                                                    configure_obj.saved_bucket,
                                                    configure_obj.saved_tmp_path,
                                                    configure_obj.saved_target_path,
                                                    configure_obj.saved_target_filename,
                                                    configure_obj.dynamodb_tablename,
                                                    configure_obj.saved_logs_target_path,
                                                    configure_obj.saved_logs_target_filename
                                                    ])

    print(f"loop task: {loop_task}")
    # for id in task_ids:
    end_hostname = socket.gethostname()
    end_host_ip = socket.gethostbyname(hostname)   
    end_status = WorkerStatus(host_name=end_hostname,task_id="process_files_from_yaml", host_ip=end_host_ip, pid = pid,function_name="process_files_from_yaml", action="busy-stop/idle-start", time=str(time.time()),message="end process files")
    end_res = put_item_to_dynamodb(configure_obj.dynamodb_tablename, workerstatus=end_status)

# ***************************        
# process all files in bucket
# ***************************      

@cli.command("process_all_files_in_bucket")
@click.argument('config_params_str', nargs=1)
@click.argument('solardata_params_str', nargs=1)
def process_all_files(config_params_str:str,solardata_params_str:str):
    
    configure_obj = make_configure_from_str(config_params_str)
    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)      
    pid = os.getpid()

    start_status = WorkerStatus(host_name=hostname,task_id="process_all_files_in_bucket", host_ip=host_ip,pid=pid, function_name="process_all_files_in_bucket", action="idle-stop/busy-start", time=str(time.time()),message="init process n files")
    start_res = put_item_to_dynamodb(configure_obj.dynamodb_tablename, workerstatus = start_status)
   
    print(f"Process all files in {configure_obj.bucket}")
    task_ids = []
    files = list_files_in_bucket(configure_obj.bucket)
    # n_files = files[0:int(5)]
    s3_client = connect_aws_client('s3')
    for file in files:
         # implement partial match 
        matched_column_set = find_matched_column_name_set(bucket_name=configure_obj.bucket, columns_key=configure_obj.column_names, file_path_name=file['Key'],s3_client=s3_client)
        for column in matched_column_set:
       
            path, filename = os.path.split(file['Key'])
            prefix = path.replace("/", "-")
            temp_saved_filename = f"{prefix}-{filename}"
            start_time = time.time()
    
            task_id = process_data_task.apply_async([
                    configure_obj.dynamodb_tablename,
                    configure_obj.bucket,
                    file['Key'],
                    column,
                    configure_obj.saved_bucket,
                    configure_obj.saved_tmp_path,
                    temp_saved_filename,
                    start_time,
                    solardata_params_str
                    ])
            task_ids.append(str(task_id)) 
    for id in task_ids:
        print(id)
    # # loop the task status in celery task
    loop_task = loop_tasks_status_task.apply_async([configure_obj.interval_of_check_task_status, 
                                                    configure_obj.interval_of_exit_check_status,
                                                    task_ids,
                                                    configure_obj.saved_bucket,
                                                    configure_obj.saved_tmp_path,
                                                    configure_obj.saved_target_path,
                                                    configure_obj.saved_target_filename,
                                                    configure_obj.dynamodb_tablename,
                                                    configure_obj.saved_logs_target_path,
                                                    configure_obj.saved_logs_target_filename
                                                    ])

    print(f"loop task: {loop_task}")
    # for id in task_ids:
    end_hostname = socket.gethostname()
    end_host_ip = socket.gethostbyname(hostname)   
    end_status = WorkerStatus(host_name=end_hostname,task_id="process_all_files_in_bucket", host_ip=end_host_ip, pid = pid,function_name="process_all_files_in_bucket", action="busy-stop/idle-start", time=str(time.time()),message="end process n files")
    end_res = put_item_to_dynamodb(configure_obj.dynamodb_tablename, workerstatus=end_status)

    return 




@app.cli.command("celery_worker")
def celery_worker():
    from watchgod import run_process
    import subprocess

    def run_worker():
        subprocess.call(
            ["celery", "-A", "app.celery", "worker", "--loglevel=info"]
        )

    run_process("./project", run_worker)







if __name__ == '__main__':
    cli()