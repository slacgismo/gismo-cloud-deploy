# # import asyncio

# # async def run(cmd: str):
# #     proc = await asyncio.create_subprocess_shell(
# #         cmd,
# #         stderr=asyncio.subprocess.PIPE,
# #         stdout=asyncio.subprocess.PIPE
# #     )

# #     stdout, stderr = await proc.communicate()

# #     print(f'[{cmd!r} exited with {proc.returncode}]')
# #     if stdout:
# #         print(f'[stdout]\n{stdout.decode()}')
# #     if stderr:
# #         print(f'[stderr]\n{stderr.decode()}')
# # task_id="4f498d17-89cc-434a-8e2e-4bb9590259dc"
# # for i in [2,3,3]:
# #     asyncio.run(run(f'docker exec -it web python app.py get_task_status {task_id}'))
# # # 4f498d17-89cc-434a-8e2e-4bb9590259dc

# # import platform, os 
# # import psutil 
# # def cpu_info(): 
# #     if platform.system() == 'Windows': 
# #         return platform.processor() 
# #     elif platform.system() == 'Darwin': 
# #         command = '/usr/sbin/sysctl -n machdep.cpu.brand_string' 
# #         return os.popen(command).read().strip() 
# #     elif platform.system() == 'Linux': 
# #         command = 'cat /proc/cpuinfo' 
# #         return os.popen(command).read().strip() 
# #     return 'platform not identified' 
 
# # # print(cpu_info()) 

# # print(psutil.Process().pid)
# # print(os.getpid())

# from ast import Constant
# import click
# import boto3
# from concurrent.futures import thread
# # from distutils.command.config import config
# import json
# import logging
# from botocore.exceptions import ClientError
# import pandas as pd
# import numpy as np
# from models.WorkerStatus import WorkerStatus, make_worker_object_from_dataframe
# from email.policy import default
# import click
# from models.Node import Node
# from concurrent.futures import thread
# from distutils.command.config import config
from kubernetes import client as k8sclient
from kubernetes import config as k8sconfig
# import json
# # from kubernetes import client as k8sclient
# # from kubernetes import config as k8sconfig

# from utils.ReadWriteIO import (read_yaml)
# import io
# import sys
# import os
# from utils.InvokeFunction import (
#     invok_docekr_exec_run_process_files,
#     invok_docekr_exec_run_process_all_files,
#     invok_docekr_exec_run_process_first_n_files,
#     invoke_eksctl_scale_node
#     )
# from typing import List

# from multiprocessing.pool import ThreadPool as Pool
# from threading import Timer
# from models.SolarParams import SolarParams
# # from models.Config import Config
# from models.Task import Task

# # from utils.aws_utils import (
# #     connect_aws_resource,
# #     connect_aws_client
# # )

# # from utils.taskThread import taskThread

# from utils.sqs import(
#     send_queue_message,
#     list_queues,
#     create_standard_queue,
#     create_fifo_queue,
#     receive_queue_message,
#     delete_queue_message,
#     clean_previous_sqs_message,
#     configure_queue_long_polling,
#     purge_queue
# )
# from utils.sns import(
#     list_topics,
#     publish_message,
#     sns_subscribe_sqs
# )

k8sconfig.load_kube_config()
v1= k8sclient.CoreV1Api()
# response = v1k8.list_node()
# nodes = []
# check confition
# config.load_kube_config()
# v1 = client.CoreV1Api()
# print("Listing pods with their IPs:")
ret = v1.list_pod_for_all_namespaces(watch=False)
pods = []
for i in ret.items:
    # print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

    podname = i.metadata.name.split("-")[0]
    if podname == "worker" or podname == "webapp" :
        pods.append(i)

# print(pods[0].status.pod_ip)
for pod in pods :
    print(pod.metadata.name, pod.spec.node_name,pod.status.pod_ip )

# config.load_incluster_config()
# config.load_kube_config()
# v1 = client.CoreV1Api()
# # res = v1.list_node()  
# container_name = "webapp"
# ret = v1.list_pod_for_all_namespaces(watch=False)
# for i in ret.items:
#     # print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
#     podname = i.metadata.name.split("-")[0]
#     if podname == container_name:
#         # print(f"podname: {i.metadata.name}")
#         print(i.metadata.name)