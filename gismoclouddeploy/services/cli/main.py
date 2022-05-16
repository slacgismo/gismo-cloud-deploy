
from ast import Constant
import click
import boto3
from concurrent.futures import thread
from distutils.command.config import config
import json
import logging
from botocore.exceptions import ClientError
import pandas as pd
import numpy as np
from models.WorkerStatus import WorkerStatus, make_worker_object_from_dataframe
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
import plotly.express as px
from multiprocessing.pool import ThreadPool as Pool
from threading import Timer
import asyncio
from models.SolarParams import SolarParams
from models.Config import Config
from models.Task import Task
from datetime import datetime
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
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
    delete_queue_message,
    configure_queue_long_polling
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
    messages = receive_queue_message(QUEUE_URL, sqs_client, wait_time=20)

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


def process_df_for_gantt(df:pd)  :
    # result = [f(row[0], ..., row[5]) for row in df[['host_ip','filename','function_name','action','column_name','timestamp']].to_numpy()]
    # print(result)
    workerstatus_list= make_worker_object_from_dataframe(df)

    # process timestamp into linear 
    # find min
    #combine task from
    worker_dict={}
    key_start = 'start'
    key_end = 'end'
    key_task = 'task'
    key_host_ip = 'host_ip'
    for worker in workerstatus_list:
        host_ip = (worker.host_ip)
        task_id =  (worker.task_id)
        if host_ip in worker_dict:
    
            if task_id in worker_dict[host_ip]:
                # print(f"exit {task_id} in {host_ip}")
                if key_start in worker_dict[host_ip][task_id]:
                    worker_dict[host_ip][task_id][key_end] = worker.time
                else:
                    worker_dict[host_ip][task_id][key_start] = worker.time
                # get duration from datetime
                end = pd.to_datetime( worker_dict[host_ip][task_id][key_end])
                start= pd.to_datetime( worker_dict[host_ip][task_id][key_start])
                worker_dict[host_ip][task_id]['duration'] = int(round((end - start).total_seconds()))

            else:
                # print(f"add new task {task_id}")
                temp_dict = {}
                worker_dict[host_ip][task_id] = {}
                if pd.isnull(worker.filename):
                    temp_dict[key_task] = worker.function_name
                else:
                    temp_dict[key_task] = worker.filename
              
                if worker.action == "busy-stop/idle-start":
                    temp_dict[key_end] = worker.time
                else:
                    temp_dict[key_start] = worker.time
                worker_dict[host_ip][task_id] = temp_dict

        else:
            info_dict = {}
            worker_dict[host_ip] = {}
            if pd.isnull(worker.filename):
                info_dict[key_task] = worker.function_name
            else:
                info_dict[key_task] = worker.filename
            if worker.action == "busy-stop/idle-start":
                info_dict[key_end] = worker.time
            else:
                info_dict[key_start] = worker.time

            worker_dict[host_ip][task_id] =info_dict
    # for worker in workerstatus_list:
    #     # print(worker.task_id)
    #     task_id = worker.task_id
    #     if task_id in worker_dict:
            # if key_start in worker_dict[task_id]:
            #     worker_dict[task_id][key_end] = worker.time
            # else:
            #     worker_dict[task_id][key_start] = worker.time
            # # get duration from datetime
            # end = pd.to_datetime( worker_dict[task_id][key_end])
            # start= pd.to_datetime( worker_dict[task_id][key_start])
            # worker_dict[task_id]['duration'] = int(round((end - start).total_seconds()))
  
            # # duration = float(worker_dict[task_id][key_end]) - float(worker_dict[task_id][key_start])
            # # worker_dict[task_id]['duration'] = duration
           
    #     else:
            # info_dict = {}
            # if pd.isnull(worker.filename):
            #     info_dict[key_task] = worker.function_name
            # else:
            #     info_dict[key_task] = worker.filename
            # # print(info_dict['task'])
            # info_dict[key_host_ip] = worker.host_ip
            # if worker.action == "busy-stop/idle-start":
            #     info_dict[key_end] = worker.time
            # else:
            #     info_dict[key_start] = worker.time
            # worker_dict[worker.task_id] = info_dict
    
    # for key in worker_dict:
    #     print(f" key :{key}")


    return worker_dict

# def addAnnot(df, fig):
#     for i in df:
#         x_pos = (i['Finish'] - i['Start'])/2 + i['Start']
#         for j in fig['data']:
#             if j['name'] == i['Label']:
#                 y_pos = (j['y'][0] + j['y'][1] + j['y'][2] + j['y'][3])/4
#         fig['layout']['annotations'] += tuple([dict(x=x_pos,y=y_pos,text=i['Label'],font={'color':'black'})])


def process_logs():
    print('process_logs')
    df = pd.read_csv('logs.csv', index_col=0, parse_dates=['timestamp'], infer_datetime_format=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'], 
                                  unit='s')

    # print(df.head())




    worker_dict = process_df_for_gantt(df)

    # # # Show dataframe
    figures = []
    subplot_titles = []
    for key , value in worker_dict.items():
        gantt_list = []
        subplot_titles.append(key)
        for k2,v2 in value.items():
            item = dict(Task=v2['task'], Start=(v2['start']), Finish=(v2['end']), Resource=f"{v2['task']}:{v2['duration']}s", Duration = v2['duration'])
    #     print(item)
            gantt_list.append(item)
        gantt_df = pd.DataFrame(gantt_list)
        
        fgg = ff.create_gantt(gantt_df, reverse_colors=True, show_colorbar=True,index_col='Resource')
        print(v2['start'])
        # fgg['layout']['annotations'] = [dict(x='2022-05-13 16:50',y=1,text="This is a label", showarrow=False, font=dict(color='purple'))]
        figures.append(fgg)
      
    figs = make_subplots(rows=len(figures), cols=1,
                    shared_xaxes=True,subplot_titles = subplot_titles)
    row = 1
    for fgg in figures:
        figs['layout'][f'yaxis{row}'].update(fgg.layout.yaxis)
        for trace in fgg.data:
            figs.add_trace(trace, row=row, col=1)
        row += 1
    figs.update_layout(
        xaxis = dict(
            tickmode = 'linear',
            tick0 = 0.5,
            dtick = 2
        )
    )
    # figs['layout'].update(
    #     annotations=[
    #     dict(x='2022-05-13 16:52:23', y=0, xref='x1', yref='y1', text='True activity', font=dict(size=10, color='green')),
    #     dict(x='2022-05-13 16:52:23', y=0, xref='x1', yref='y2', text='Model', font=dict(size=10, color='blue')),
    #     dict(x='2022-05-13 16:52:23', y=0, xref='x1', yref='y3', text='ALO', font=dict(size=10, color='red')),
    #     ]
    # )
    figs.show()
    # fig = px.timeline(gantt_df, x_start="Start", x_end="Finish", y="Task",color="Resource")
    # fig = px.timeline(gantt_df, x_start="Start", x_end="Finish",y="Task",color="Resource",opacity=0.8, facet_row='Resource',text='Duration',)
    # fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up

    # fig.show()


    # df = [dict(Task="Job A", Start='2022-01-01', Finish='2022-02-28'),
    # dict(Task="Job B", Start='2022-03-05', Finish='2022-04-15'),
    # dict(Task="Job C", Start='2022-02-20', Finish='2022-05-30')]

    # fig = px.timeline(df, x_start='Start', x_end='Finish', color='Task', title='Gantt Chart', hover_name='Task', text='Task', opacity=0.8, facet_row='Task')
    # fig.show()
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
def processlogs():
    """"Try sqs"""
    process_logs()

@main.command()
@click.argument('text')
def capitalize(text):
	"""Capitalize Text"""
	click.echo(text.upper())

if __name__ == '__main__':
	main()