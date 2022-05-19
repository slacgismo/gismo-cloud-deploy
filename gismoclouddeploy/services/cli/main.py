
from ast import Constant
import click
import boto3
import time
from concurrent.futures import thread
# from distutils.command.config import config
import json
import logging
from botocore.exceptions import ClientError
import pandas as pd
import numpy as np
from models.WorkerStatus import WorkerStatus, make_worker_object_from_dataframe
from email.policy import default
import click
from models.Node import Node
from concurrent.futures import thread
# from distutils.command.config import config
from kubernetes import client, config
import json
# from kubernetes import client as k8sclient
# from kubernetes import config as k8sconfig

from utils.ReadWriteIO import (read_yaml)
import io
import sys
import os
from utils.InvokeFunction import (
    invok_docekr_exec_run_process_files,
    invok_docekr_exec_run_process_all_files,
    invok_docekr_exec_run_process_first_n_files,
    invoke_eksctl_scale_node
    )
from typing import List
import plotly.express as px
from multiprocessing.pool import ThreadPool as Pool
from threading import Timer
import asyncio
from models.SolarParams import SolarParams
from models.Config import Config
from models.Task import Task

from utils.aws_utils import (
    connect_aws_resource,
    connect_aws_client
)

from utils.eks_utils import(
    num_of_nodes_ready,
    scale_node_number,
    scale_nodes_and_wait,
    wait_container_ready
)

from utils.taskThread import (
    taskThread
)

from utils.aws_utils import (
    check_environment_is_aws
)

from utils.sqs import(
    send_queue_message,
    list_queues,
    create_standard_queue,
    create_fifo_queue,
    receive_queue_message,
    delete_queue_message,
    clean_previous_sqs_message,
    configure_queue_long_polling,
    purge_queue
)
from utils.sns import(
    list_topics,
    publish_message,
    sns_subscribe_sqs
)



# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')

from dotenv import load_dotenv
load_dotenv()
SQS_URL = os.getenv('SQS_URL')
SQS_ARN = os.getenv('SQS_ARN')
SNS_TOPIC = os.getenv('SNS_TOPIC')

def init_standard_sqs():
    QUEUE_NAME = 'gcd-standard-queue'
    DELAY_SECONDS = '0'
    VISIBLITY_TIMEOUT = '60'
    sqs_resource = connect_aws_resource('sqs')
    output = create_standard_queue(QUEUE_NAME, DELAY_SECONDS, VISIBLITY_TIMEOUT,sqs_resource)
    print(output)

def init_fifo_sqs():
    QUEUE_NAME = 'gismo-cloud-deploy-sqs.fifo'
    DELAY_SECONDS = '0'
    VISIBLITY_TIMEOUT = '60'
    sqs_resource = connect_aws_resource('sqs')
    output = create_fifo_queue(QUEUE_NAME, DELAY_SECONDS, VISIBLITY_TIMEOUT,sqs_resource)
    print(f"sqs {output}")

def try_send_and_receive_queue_message():
    # send message
    # CONSTANTS
    QUEUE_URL = SQS_URL
    MSG_ATTRIBUTES = {
        'Title': {
            'DataType': 'String',
            'StringValue': 'Working with SQS in Python using Boto3'
        },
        'Author': {
            'DataType': 'String',
            'StringValue': 'Abhinav D'
        }
    }
    MSG_BODY = 'Learn how to create, receive, delete and modify SQS queues and see the other functions available within the AWS.'
    sqs_client = connect_aws_client('sqs')
    msg = send_queue_message(QUEUE_URL, MSG_ATTRIBUTES, MSG_BODY,sqs_client)

    json_msg = json.dumps(msg, indent=4)

    logger.info(f'''
        Message sent to the queue {QUEUE_URL}.
        Message attributes: \n{json_msg}''')
    # receive message
    print("Receive message ---->")
    messages = receive_queue_message(QUEUE_URL, sqs_client, wait_time=20)

    for msg in messages['Messages']:
        msg_body = msg['Body']
        receipt_handle = msg['ReceiptHandle']

        logger.info(f'The message body: {msg_body}')

        logger.info('Deleting message from the queue...')

        delete_queue_message(QUEUE_URL, receipt_handle, sqs_client)

    logger.info(f'Received and deleted message(s) from {QUEUE_URL}.')


def subscribe_sns():
    topic_arn = SNS_TOPIC
    endpoint = SQS_ARN
    logger.info('Subscribing to a SNS topic...')
    sns_client = connect_aws_client('sns')
    # Creates an email subscription
    response = sns_subscribe_sqs(topic=topic_arn, endpoint=endpoint,sns_client=sns_client)

def public_message_to_sns():
    sns_client = connect_aws_client('sns')
    topic_arn = SNS_TOPIC
    message = 'This is a test message on topic.'
    subject = 'This is a message subject on topic.'
    logger.info(f'Publishing message to topic - {topic_arn}...')
    message_id = publish_message( message = message, topic_arn=topic_arn, sns_client=sns_client)
    logger.info(
        f'Message published to topic - {topic_arn} with message Id - {message_id}.'
    )

def list_sns():
    # topic= create_sns_topic('gismo-cloud-deploy-sns')
    # list_topic= list_topics()
    sns_resource = connect_aws_resource('sns')
    for topic in list_topics(sns_resource):
        print(topic)
    # print(f"start sns {list_topic}")





def run_process_files(number):
    # import parametes from yaml
    solardata_parmas_obj = SolarParams.import_solar_params_from_yaml("./config/config.yaml")
    config_params_obj = Config.import_config_from_yaml("./config/config.yaml")
    # step 1 . check node status
    if check_environment_is_aws():
        scale_nodes_and_wait(3, 60, 1)
        # step 1.1 wait pod ready 
        wait_container_ready( num_container=3, container_prefix="worker",counter=60, delay=1 )
    # step 2 . clear sqs
    print("clean previous sqs")
    sqs_client = connect_aws_client('sqs')
    # purge_res = purge_queue(queue_url=SQS_URL, sqs_client=sqs_client)
    clean_previous_sqs_message(sqs_url=SQS_URL, sqs_client=sqs_client, wait_time=2)


    if number is None:
        print("process default files in config.yaml")
        res = invok_docekr_exec_run_process_files(config_obj = config_params_obj,
                                        solarParams_obj= solardata_parmas_obj,
                                        container_type= config_params_obj.container_type, 
                                        container_name=config_params_obj.container_name)
        print(f"response : {res}")
    elif number == "n":
        print("process all files")
        res = invok_docekr_exec_run_process_all_files( config_params_obj,solardata_parmas_obj, config_params_obj.container_type, config_params_obj.container_name)
        print(f"response : {res}")
    else:
        if type(int(number)) == int:
            print(f"process first {number} files")
            res = invok_docekr_exec_run_process_first_n_files( config_params_obj,solardata_parmas_obj, number, config_params_obj.container_type, config_params_obj.container_name)
        #     print(f"response : {res}")
        #     # process long pulling
        #     total_task_num = int(number) + 1  # extra task for save results , logs and plot logs
        #     thread = taskThread(1,"sqs",120,2,SQS_URL,total_task_num)
        #     thread.start()
            
        # else:
        #     print(f"error input {number}")

    return 





def check_nodes_status():
    # print("check node status")
    config.load_kube_config()
    v1 = client.CoreV1Api()
    response = v1.list_node()
    nodes = []
    # check confition
    for node in response.items:

        # print(node.metadata.labels['kubernetes.io/hostname'])
        cluster = node.metadata.labels['alpha.eksctl.io/cluster-name']
        nodegroup = node.metadata.labels['alpha.eksctl.io/nodegroup-name']
        hostname = node.metadata.labels['kubernetes.io/hostname']
        instance_type = node.metadata.labels['beta.kubernetes.io/instance-type']
        region = node.metadata.labels['topology.kubernetes.io/region']
        status = node.status.conditions[-1].status # only looks the last 
        status_type = node.status.conditions[-1].type # only looks the last
        node_obj = Node(cluster=cluster, 
                        nodegroup = nodegroup, 
                        hostname=hostname,
                        instance_type = instance_type,
                        region= region ,
                        status = status,
                        status_type = status_type
                        )

        nodes.append(node_obj)
        if bool(status) != True:
            print(f"{hostname} is not ready status:{status}")
            return False
    for node in nodes:
        print(f"{node.hostname} is ready")
    return True




def publish_receive_sns():
    print("publish sns")
    public_message_to_sns()
    print("receive sns")
    print("Receive message ---->")
    sqs_client = connect_aws_client('sqs')
    messages = receive_queue_message(SQS_URL, sqs_client, wait_time=20)

    for msg in messages['Messages']:
        msg_body = msg['Body']
        receipt_handle = msg['ReceiptHandle']

        logger.info(f'The message body: {msg_body}')

        logger.info('Deleting message from the queue...')

        delete_queue_message(QUEUE_URL, receipt_handle, sqs_client)

    logger.info(f'Received and deleted message(s) from {QUEUE_URL}.')

       


def longpulling_thread():
    print("long pulling")
    thread = taskThread(1,"sqs",60,2,SQS_URL)
    thread.start()


# Parent Command
@click.group()
def main():
	pass



# Run files 
@main.command()
@click.option('--number','-n',
            help="Process the first n files in bucket, if number=n, run all files in the bucket", 
            default= None)
def run_files(number):
    """ Run Process Files"""
    run_process_files(number)

@main.command()
@click.argument('min_nodes')
def nodes_scale(min_nodes):
    """Increate or decrease nodes number"""
    scale_node_number(min_nodes)

@main.command()
# @click.argument('min_nodes')
def check_nodes():
    """ Check nodes status """
    check_nodes_status()

@main.command()
def longpulling():
    """Try thread"""
    longpulling_thread()
    
@main.command()
def listsns():
    """"Try SNS"""
    list_sns()

@main.command()
def createsqs():
    """"Try sqs"""
    init_standard_sqs()

@main.command()
def sns_public_message():
    """"Try sns"""
    public_message_to_sns()


@main.command()
def listsqs():
    """"Try sqs"""
    sqs_resource = connect_aws_resource('sqs')
    list_queues(sqs_resource)
@main.command()
def subscribesns():
    """"Try sqs"""
    subscribe_sns()

@main.command()
def publish_and_receive_sns():
    """"Try sqs"""
    publish_receive_sns()

@main.command()
def trysqs():
    """"Try sqs"""
    try_send_and_receive_queue_message()

@main.command()
def processlogs():
    """"Try sqs"""
    from utils.process_log import process_logs
    process_logs()









if __name__ == '__main__':
	main()