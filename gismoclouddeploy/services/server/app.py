from curses import flash
from itertools import count
import logging

from numpy import save

# from project import create_app, ext_celery,db
from project import create_app, ext_celery
from flask.cli import FlaskGroup
from flask import jsonify
import json
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
    read_csv_from_s3_with_column_and_time,
    put_item_to_dynamodb,

    remove_all_items_from_dynamodb,
    retrive_all_item_from_dyanmodb,
    save_logs_from_dynamodb_to_s3)
import click
from celery.result import AsyncResult
import time
import os 
from project.solardata.tasks import (
    read_all_datas_from_solardata,
    save_data_from_db_to_s3_task,
    process_data_task,
    combine_files_to_file_task,
    loop_tasks_status_task,
    plot_gantt_chart_from_log_files_task,
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
    for file in n_files:
        for column in configure_obj.column_names:
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
    # loop the task status in celery task
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
    # print(f"end_res {end_res}")
# ***************************        
# Process multiple files
# ***************************   



@cli.command("process_files")
@click.argument('config_params_str', nargs=1)
@click.argument('solardata_params_str', nargs=1)

def process_files( config_params_str:str,
                    solardata_params_str:str,               
                    ):
    # convert command str to json format and pass to object
    configure_obj = make_configure_from_str(config_params_str)
    logger.info(f'''Start plot gantt chart''')
    bucket = configure_obj.saved_bucket
    log_file_path_name = configure_obj.saved_logs_target_path +"/"+ configure_obj.saved_logs_target_filename
    save_file="results/runtime.pdf"
    task = plot_gantt_chart_from_log_files_task.apply_async([bucket, log_file_path_name,save_file])
    print(f"task {task}")
    # print(config_params_str)
    
    # task_ids = []
    # for file in configure_obj.files:
    #     for column in configure_obj.column_names:
    #         path, filename = os.path.split(file)
    #         prefix = path.replace("/", "-")
    #         temp_saved_filename = f"{prefix}-{filename}"
    #         start_time = time.time()
    #         # print(f"temp_saved_filename: {temp_saved_filename}")
    #         task_id = process_data_task.apply_async([
    #                 configure_obj.bucket,
    #                 file,
    #                 column,
    #                 configure_obj.saved_bucket,
    #                 configure_obj.saved_tmp_path,
    #                 temp_saved_filename,
    #                 start_time,
    #                 solardata_params_str
    #                 ])
    #         task_ids.append(task_id)
    # print(task_ids)
    # # for id in task_ids:
    # #     res = AsyncResult(str(id))
    # #     print(f"schedulers: id: {res.task_id} \n task status: {res.status}, ")
    # counter = 40
    # num_success_task = 0
 
    # while counter > 0:
    #     # check the task status
    #     time.sleep(1)
    #     for id in task_ids:
    #         res = AsyncResult(str(id))
    #         status = str(res.status)
           
    #         if status == "SUCCESS":
    #             print(f"schedulers: id: {res.task_id} \n task status: {res.status}, Time: {time.ctime(time.time())}")
    #             # print(f"schedulers: id: {res.task_id} \n task status: {res.status}, Time: {time.ctime(time.time())}")
    #             print("get success task")
    #             num_success_task += 1
    #     if num_success_task == len(task_ids):
    #         print(f"num_success_task: {num_success_task}")
    #         break 
    #     counter -= 1

    # print("Start combine files")
    # print(f"bucket_name: {configure_obj.saved_bucket} ,source_folder {configure_obj.saved_tmp_path} ,target_folder: {configure_obj.saved_target_path},target_filename: {configure_obj.saved_target_filename}")
    # task = combine_files_to_file_task.apply_async(
    #     [configure_obj.saved_bucket,
    #     configure_obj.saved_tmp_path,
    #     configure_obj.saved_target_path,
    #     configure_obj.saved_target_filename
    #     ])
    # print("combile files task : {task}")

# ***************************        
# process all files in bucket
# ***************************      

@cli.command("process_all_files_in_bucket")
@click.argument('config_params_str', nargs=1)
@click.argument('solardata_params_str', nargs=1)
def process_all_files(config_params_str:str,solardata_params_str:str):
    
    # convert command str to json format and pass to object
    configure_obj = make_configure_from_str(config_params_str)
    # solar_params_obj = make_solardata_params_from_str(solardata_params_str)
    # get all csv files in bucket 
    task_ids = []
    files = list_files_in_bucket(configure_obj.bucket)
    # print(files)
    for file in files:
        for column in configure_obj.column_names:

            path, filename = os.path.split(file['Key'])
            prefix = path.replace("/", "-")
            temp_saved_filename = f"{prefix}-{filename}"
            print(f"temp_saved_filename {temp_saved_filename}")
            start_time = time.time()
            task_id = process_data_task.apply_async([
                    configure_obj.bucket,
                    file['Key'],
                    column,
                    configure_obj.saved_bucket,
                    configure_obj.saved_tmp_path,
                    temp_saved_filename,
                    start_time,
                    solardata_params_str
                    ])
            task_ids.append(task_id)
            # print(f"df {df.head()}")
            # if df.empty:
            #     print(f"file: {file} column : {column} is empty" )
            # print(f"df {df}")
        


    # process data and resture task status

    # run a thread to process task status 

    return "proess all"

@cli.command("get_task_status")    
@click.argument('task_id', nargs=1)
def get_task_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status":task_result.status,
        "task_result":task_result.result
    }
    print(f"{result}")




@app.cli.command("celery_worker")
def celery_worker():
    from watchgod import run_process
    import subprocess

    def run_worker():
        subprocess.call(
            ["celery", "-A", "app.celery", "worker", "--loglevel=info"]
        )

    run_process("./project", run_worker)


# def check_status(threadName:str, task:Task, counter:int, delay:int, config:Config) -> None:
#     while counter:
#         response = invoke_docker_exec_get_task_status(task.task_id, config.container_type, config.container_name)
#         # parse response 
#         json_obj = json.loads(response.replace('None', "\'None\'").replace("\'","\""))
#         print(f"response: {json_obj}")
#         response_status = json_obj['task_status']
#         if response_status == "SUCCESS":
#             print("Task Success ")
#             break
        
#         # print (f"task id: {task.task_id}, task status: {task.task_status}, Time: {time.ctime(time.time())}")
#         time.sleep(delay)
        
#         counter -= 1
import threading
import time
class taskThread (threading.Thread):
    def __init__(self, threadID:int, name:str, delay:int,task_ids ):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.task_ids = task_ids
        self.delay = delay

    def run(self):
      print ("Starting " + self.name)
      check_status(self.name, 5, self.delay,self.task_ids )
      print ("Exiting " + self.name)

exitFlag = 0 

def check_status(threadName:str, counter:int, delay:int, task_ids: List[str]) -> None:
    num_of_pending = len(task_ids)
    while counter or num_of_pending > 0:
        num_of_pending = 0 
        if exitFlag:
            break
        for id in task_ids:
            task_result = AsyncResult(id)
            status = task_result.status
            if status == "PENDING":
                num_of_pending += 1
        print (f"Time: {time.ctime(time.time())},num_of_pending: {num_of_pending} ")
        time.sleep(delay)
        counter -= 1
    print("END of threading ")
        # response = invoke_docker_exec_get_task_status(task.task_id, config.container_type, config.container_name)
        # parse response 
        # json_obj = json.loads(response.replace('None', "\'None\'").replace("\'","\""))
        # print(f"response: {json_obj}")
        # response_status = json_obj['task_status']
        # if response_status == "SUCCESS":
        #     print("Task Success ")
        #     break
        
       
        



if __name__ == '__main__':
    cli()