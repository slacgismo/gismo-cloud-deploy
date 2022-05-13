
from ast import Constant
import click
import boto3
from concurrent.futures import thread
from distutils.command.config import config
import json
import logging
from botocore.exceptions import ClientError


from utils.ReadWriteIO import (read_yaml)
import io
import sys
import os
from utils.InvokeFunction import (
    invok_docekr_exec_run_process_files,
    invok_docekr_exec_run_process_all_files,
    invok_docekr_exec_run_process_first_n_files
    )
from typing import List

from multiprocessing.pool import ThreadPool as Pool
from threading import Timer
import asyncio
from models.SolarParams import SolarParams
from models.Config import Config
from models.Task import Task
# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')

SQS_URL='https://us-east-2.queue.amazonaws.com/041414866712/gcd-standard-queue' 

def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        response = client.list_buckets()
        return True

    except Exception as e:
        if str(e)!="An error occurred (InvalidAccessKeyId) when calling the ListBuckets operation: The AWS Access Key Id you provided does not exist in our records.":
            return True
        return False

def connect_aws_client(client_name):
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION')
    if check_aws_validity(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY) :
        client = boto3.client(
            client_name,
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key= AWS_SECRET_ACCESS_KEY
        )
        return client
    raise Exception('AWS Validation Error')

def connect_aws_resource(resource_name):
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION')
    if check_aws_validity(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY) :
        resource = boto3.resource(
            resource_name,
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key= AWS_SECRET_ACCESS_KEY
        )
        return resource
    raise Exception('AWS Validation Error')



from utils.sqs import(
    send_queue_message,
    list_queues,
    create_standard_queue,
    create_fifo_queue,
    receive_queue_message,
    delete_queue_message
)
from utils.sns import(
    list_topics
)
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
    messages = receive_queue_message(QUEUE_URL, sqs_client)

    for msg in messages['Messages']:
        msg_body = msg['Body']
        receipt_handle = msg['ReceiptHandle']

        logger.info(f'The message body: {msg_body}')

        logger.info('Deleting message from the queue...')

        delete_queue_message(QUEUE_URL, receipt_handle, sqs_client)

    logger.info(f'Received and deleted message(s) from {QUEUE_URL}.')




def run_sns():
    # topic= create_sns_topic('gismo-cloud-deploy-sns')
    # list_topic= list_topics()
    for topic in list_topics():
        print(topic)
    # print(f"start sns {list_topic}")

def run_process_files(number):
    # import parametes from yaml
    solardata_parmas_obj = SolarParams.import_solar_params_from_yaml("./config/config.yaml")
    config_params_obj = Config.import_config_from_yaml("./config/config.yaml")


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
            print(f"response : {res}")
        else:
            print(f"error input {number}")
    
    return 




# Parent Command
@click.group()
def main():
	pass

# Run files 
@main.command()
@click.option('--number','-n',help="Process the first n files in bucket, if number=n, run all files in the bucket", default= None)
def run_files(number):
    """ Run Process Files"""
    run_process_files(number)

@main.command()
def trysns():
    """"Try SNS"""
    run_sns()

@main.command()
def createsqs():
    """"Try sqs"""
    init_standard_sqs()

@main.command()
def listsqs():
    """"Try sqs"""
    sqs_resource = connect_aws_resource('sqs')
    list_queues(sqs_resource)
    
@main.command()
def trysqs():
    """"Try sqs"""
    try_send_and_receive_queue_message()

@main.command()
@click.argument('text')
def capitalize(text):
	"""Capitalize Text"""
	click.echo(text.upper())

if __name__ == '__main__':
	main()