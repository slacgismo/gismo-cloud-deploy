

from distutils.command.config import config
import json
from utils.ReadWriteIO import (read_yaml)
import io
import sys
import os
from utils.InvokeFunction import invok_docekr_exec_run_process_file, invoke_docker_exec_get_task_status, invoke_docker_exec_combine_files
from typing import List

from multiprocessing.pool import ThreadPool as Pool
from threading import Timer
import asyncio
from models.Solardata import Solardata
from models.Config import Config

# class CustomTimer(Timer):
#     def __init__(self, interval, function, args=[], kwargs={}):
#         self._original_function = function
#         super(CustomTimer, self).__init__(
#             interval, self._do_execute, args, kwargs)

#     def _do_execute(self, *a, **kw):
#         self.result = self._original_function(*a, **kw)

#     def join(self):
#         super(CustomTimer, self).join()
#         return self.result


solardata = Solardata.import_solardata_from_yaml("./config/config.yaml")
config_params = Config.import_config_from_yaml("./config/config.yaml")



# def run_process_files(bucket, files, column_names, solver, saved_bucket, saved_file_path, container_type, container_name):
def run_process_files(config: Config, solardata: Solardata) -> List[str]:
    task_ids = []
    for file in config.files:
        for col_name in config.column_names:
            path, filename = os.path.split(file)

            prefix = path.replace("/", "-")
            tem_saved_filename = f"{prefix}-{filename}"
            print(
                f"bucket:{config.bucket} path:{path} filename:{filename},col_name:{col_name},solver:{solardata.solver}")
            task_id = invok_docekr_exec_run_process_file(
                config.bucket, path, filename, col_name, solardata.solver, config.saved_bucket, config.saved_tmp_path, tem_saved_filename, config.container_type, config.container_name,)
            if task_id:
                key, value = task_id.replace(
                    " ", "").replace("\n", "").split(":")
                task_ids.append({key: value, "task_status": "PENDING"})
      
    print(task_ids)
    return task_ids


def check_status(ids: List[str], config:Config):
    for id in ids:
        response = invoke_docker_exec_get_task_status(
            id, config.container_type, config.container_name)
        # data = json.load(response)
        print(f"response: {response}, id {id}, task_status: ")


def combine_files_and_clean(config: Config) -> str:
    """Combines all tmp result files into one and deleted tmp result files"""
    task_id = invoke_docker_exec_combine_files(config)
    return task_id

task_ids = run_process_files(config_params, solardata)
check_status(task_ids, config_params)
# def add_together(a, b):
#     return a + b
# task_id = combine_files_and_clean(config_params)
# print(task_id)
# c = CustomTimer(1, add_together, (2, 4))
# c = CustomTimer(1,invoke_docker_exec_get_task_status,("3a6ccb65-2ec0-4732-8fbd-33954f7b058e"))
# c.start()
# print (c.join())

# from multiprocessing import Pool
# pool_size = 5
# # define worker function before a Pool is instantiated
# def worker(item):
#     try:
#         # print(f"item: {item}")
#         asyncio.run(test())

#     except:
#         print('error with item')

# pool = Pool(pool_size)

# for item in ["1","2"]:
#     pool.apply_async(worker, (item))

# pool.close()
# pool.join()


# async def test(item):
#     while True:
#         print(f"Hello {item}")
#         await asyncio.sleep(2)


# get task_ids
#
# task_ids = run_process_files(bucket, files, column_names, solver,saved_bucket,saved_path,container_type,container_name)
# # print("---- end of sending task---------")
# # #  process long pulling
# task_ids = ["20dbd71d-7ccd-4a57-8966-8b5dfc0594e3"]
# check_status(task_ids)
# json_data = '[{"Detail":" Rs. 2000 Topup Rs.1779.99 Talktime","Amount":"2000","Validity":"Unlimited"},{"Detail":" Rs. 1900 Topup Rs.1690.99 Talktime","Amount":"1900","Validity":"Unlimited"}]'
# json_data ="[{"task_id":"20dbd71d-7ccd-4a57-8966-8b5dfc0594e3", "task_status":"SUCCESS", "task_result:True}]"
# # convert to python data structure
# d_list = json.loads(json_data)
# for d in d_list:
#     # use get for safety
#     print (d.get('Detail'))
#     print (d.get('Amount'))
# from time import sleep

# def hello(name):
#     print ("Hello %s!" % name)

# print ("starting...")
# rt = RepeatedTimer(1, hello, "World") # it auto-starts, no need of rt.start()
# try:
#     sleep(5) # your long-running job goes here...
# finally:
#     rt.stop() # better in a try/finally block to make sure the program ends!


# get_k8s_pod_name()

# Configs can be set in Configuration class directly or using helper utility
