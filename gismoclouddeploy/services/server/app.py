from curses import flash
from project import create_app, ext_celery,db
from flask.cli import FlaskGroup
from flask import jsonify
import json
from typing import List
from project.solardata.models.SolarParams import SolarParams
from project.solardata.models.SolarParams import make_solardata_params_from_str
from project.solardata.models.Configure import Configure
from project.solardata.models.Configure import make_configure_from_str
from project.solardata.utils import list_files_in_bucket,connect_aws_client
import click
from celery.result import AsyncResult
import time
import os 
from project.solardata.tasks import (
    read_all_datas_from_solardata,
    save_data_from_db_to_s3_task,
    process_data_task,
    combine_files_to_file_task
)


app = create_app()
celery = ext_celery.celery

cli = FlaskGroup(create_app=create_app)




@app.route("/")
def hello_world():
    return "Hello, World!"

@cli.command("hi")
def hi():
    print("hello world")
    return "Hello, World!"



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
    
# @cli.command("read_data_from_db")
# def read_data_from_db():
#     task = read_all_datas_from_solardata.delay()
#     print(f"task id : {task.id}")


@cli.command("process_files")
@click.argument('config_params_str', nargs=1)
@click.argument('solardata_params_str', nargs=1)

def process_files( config_params_str,
                    solardata_params_str
                    ):
    # convert command str to json format and pass to object
    configure_obj = make_configure_from_str(config_params_str)

    task_ids = []
    for file in configure_obj.files:
        for column in configure_obj.column_names:
            path, filename = os.path.split(file)
            prefix = path.replace("/", "-")
            temp_saved_filename = f"{prefix}-{filename}"
            start_time = time.time()
            # print(f"temp_saved_filename: {temp_saved_filename}")
            task_id = process_data_task.apply_async([
                    configure_obj.bucket,
                    file,
                    column,
                    configure_obj.saved_bucket,
                    configure_obj.saved_tmp_path,
                    temp_saved_filename,
                    start_time,
                    solardata_params_str
                    ])
            task_ids.append(task_id)
    print(task_ids)
    # pending_task = task_ids
    # success_task = []
    # delay = 1
    # counter = 8
    # for id in task_ids:
    #     res = AsyncResult(id, app= app)
    #     print(res)
    # th = taskThread(1,"thtest", 1, task_ids= task_ids )
    # th.start()

    # while counter > 0:
    #     print (f"counter: {counter}")
    #     counter -=1 
    #     time.sleep(delay)
 
    # while counter == 0:
    #     print (f"counter: {counter}")
    #     # pending_task.clear() 
    #     for id in task_ids:
    #         task_result = AsyncResult(id)
    #         if task_result.status == "PENDING":
    #             pending_task.append(id)
    #         elif task_result.status == "SUCCESS":
    #             success_task.append(id)
            
    #     time.sleep(delay)
    #     for id in pending_task:
    #         print(f"pending id : {id}")
    #     counter -= 1
        

@cli.command("process_all_files_in_bucket")
@click.argument('config_params_str', nargs=1)
@click.argument('solardata_params_str', nargs=1)
def process_all_files(config_params_str:str,solardata_params_str:str):
    
    # convert command str to json format and pass to object
    configure_obj = make_configure_from_str(config_params_str)
    solar_params_obj = make_solardata_params_from_str(solardata_params_str)
    # get all csv files in bucket 
    files = list_files_in_bucket(configure_obj.bucket)
    for file in files:
        for column in configure_obj.column_names:
            # print(file['Key'])
            s3_client = connect_aws_client('s3')
            df = read_csv_from_s3_column_names(configure_obj.bucket,file['Key'],[f"{column}"],s3_client)
            # fileter out the cloumn name didn't exit or column has no value
            if df.empty:
                print(f"file: {file} column : {column} is empty" )
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