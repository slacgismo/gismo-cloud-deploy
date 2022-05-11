

from concurrent.futures import thread
from distutils.command.config import config
import json

from utils.ReadWriteIO import (read_yaml)
import io
import sys
import os
from utils.InvokeFunction import (
    invok_docekr_exec_run_process_files,
    invok_docekr_exec_run_process_all_files
    )
from typing import List

from multiprocessing.pool import ThreadPool as Pool
from threading import Timer
import asyncio
from models.SolarParams import SolarParams
from models.Config import Config
from models.Task import Task




# def run_process_files(config:Config, solardata: Solardata) -> List[Task]:
#     task_objs= []
#     for file in config.files:
#         for col_name in config.column_names:
#             path, filename = os.path.split(file)

#             prefix = path.replace("/", "-")
#             tem_saved_filename = f"{prefix}-{filename}"
#             print(
#                 f"bucket:{config.bucket} path:{path} filename:{filename},col_name:{col_name},solardata:{solardata}")
#             task_id =  invok_docekr_exec_run_process_file(
#                 config.bucket, path, filename, col_name, solardata, config.saved_bucket, config.saved_tmp_path, tem_saved_filename, config.container_type, config.container_name,)
#             # if task_id:
#             #     key, value = task_id.replace(" ", "").replace("\n", "").split(":")
#             #     task = Task(value, "PENDING", None)
#             #     task_objs.append(task)
#                 # task_ids.append({key: value, "task_status": "PENDING"})
      
#     return task_objs


def process_files(config:Config, solarParams:SolarParams) :

    invok_docekr_exec_run_process_files(config = config,
                                        solardata_params= solarParams,
                                        container_type= config.container_type, 
                                        container_name=config.container_name)


# def check_status(ids: List[str], config:Config):
#     for id in ids:
#         response = invoke_docker_exec_get_task_status(
#             id, config.container_type, config.container_name)
#         # data = json.load(response)
#         print(f"response: {response}, id {id}, task_status:   ")


# def combine_files_and_clean(config: Config) -> str:
#     """Combines all tmp result files into one and deleted tmp result files"""
#     task_id = invoke_docker_exec_combine_files(config)
#     return task_id


# import threading
# import time

# exitFlag = 0


# class taskThread (threading.Thread):
#     def __init__(self, threadID:int, name:str, task:Task, delay:int, config:Config):
#         threading.Thread.__init__(self)
#         self.threadID = threadID
#         self.name = name
#         self.task = task
#         self.delay = delay
#         self.config = config

#     def run(self):
#       print ("Starting " + self.name)
#       check_status(self.name, self.task, 5, self.delay, self.config)
#       print ("Exiting " + self.name)


# def check_status(threadName:str, task:Task, counter:int, delay:int, config:Config) -> None:
#     while counter:
#         if exitFlag:
#             break
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



if __name__ == "__main__":


    solardata_parmas_obj = SolarParams.import_solar_params_from_yaml("./config/config.yaml")
    config_params_obj = Config.import_config_from_yaml("./config/config.yaml")
    # work
    # res = invok_docekr_exec_run_process_files(config_obj = config_params_obj,
    #                                     solarParams_obj= solardata_parmas_obj,
    #                                     container_type= config_params_obj.container_type, 
    #                                     container_name=config_params_obj.container_name)
    # res = process_files(config=config_params_obj,solarParams=solardata_parmas_obj)
    # res = invok_docekr_exec_run_process_all_files( config_params_obj,solardata_parmas_obj, config_params_obj.container_type, config_params_obj.container_name)
    # print(f"res {res}")



    # files = config_json["files"][0]
    # print(files)
    # str = parse_solardata_to_json_str(solardata).replace("\'","\"")
    # # print(str)
    # print(json.loads(str))

    # run all files
    
    # print("------- check task status ---------")
    # tasks = run_process_files(config_params, solardata)

    # for task in tasks:
    #     print(f"task id {task.task_id}, status: {task.task_status}")
    #     check_status(task.task_id, task, 5, 1, config_params)
    # print("------- end of task status ---------")
    # save_rsult = combine_files_and_clean(config_params)
    # print("Save result success")
    # index = 0 
    # for task in tasks:
        # thread = taskThread(index,task.task_id,task, 1,config_params )
        # thread.start()
    #     index += 1
  
        
