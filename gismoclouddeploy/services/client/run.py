

from utils.ReadWriteIO import (read_yaml)
import io
import sys
import os
from utils.InvokeFunction import invok_docekr_exec_run_process_file, invoke_docker_exec_get_task_status

from multiprocessing.pool import ThreadPool as Pool
from threading import Timer
import asyncio


class CustomTimer(Timer):
    def __init__(self, interval, function, args=[], kwargs={}):
        self._original_function = function
        super(CustomTimer, self).__init__(
            interval, self._do_execute, args, kwargs)

    def _do_execute(self, *a, **kw):
        self.result = self._original_function(*a, **kw)

    def join(self):
        super(CustomTimer, self).join()
        return self.result


files_config = read_yaml("./config/run-files.yaml")
files = files_config['files_config']['files']
bucket = files_config['files_config']['bucket']
column_names = files_config['files_config']['column_names']

sdt_params = read_yaml("./config/sdt-params.yaml")
solver = sdt_params['solardata']['solver']

gen_config =  read_yaml("./config/general.yaml")
environment = gen_config['general']['environment']
container_type = gen_config['general']['container_type']
container_name = gen_config['general']['container_name']





def run_process_files(bucket, files, column_names, solver):
    task_ids = []
    for file in files:
        for col_name in column_names:
            path, filename = os.path.split(file)
            # print(f"head {head} {tail}")
            print(f"bucket:{bucket} path:{path} filename:{filename},col_name:{col_name},solver:{solver}")
            task_id = invok_docekr_exec_run_process_file(bucket,path, filename, col_name, solver,container_type,container_name )
            if task_id :
                key,value = task_id.replace(" ","").replace("\n","").split(":")
                task_ids.append({key:value, "task_status":"PENDING"})
                # print(f"file: {file},col_name: {col_name} ,solver:{solver}")
    print(task_ids)
    return task_ids

import json
def check_status(ids):
    for id in ids:
        response = invoke_docker_exec_get_task_status(id)
        # data = json.load(response)
        print(f"response: {response}, id {id}, task_status: ")

# def add_together(a, b):
#     return a + b

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
task_ids = run_process_files(bucket, files, column_names, solver)
# # print("---- end of sending task---------")
# # #  process long pulling
# task_ids = ["20dbd71d-7ccd-4a57-8966-8b5dfc0594e3"]
check_status(task_ids)
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
