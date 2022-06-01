
from cmath import log
import click

from models.Node import Node

import logging

import click
import time
from kubernetes import client, config

import os
from utils.invoke_function import (
    invoke_docekr_exec_run_process_files,
    invoke_docekr_exec_run_process_first_n_files,
    )
from models.SolarParams import SolarParams
from models.Config import Config


from utils.aws_utils import (
    connect_aws_client
)

from utils.eks_utils import(
    scale_nodes_and_wait,
    create_or_update_k8s
)

from utils.taskThread import (
    taskThread,
)

from utils.aws_utils import (
    list_files_in_bucket,
    check_aws_validity
)

from utils.sqs import(

    clean_previous_sqs_message,
    receive_queue_message,
    delete_queue_message
)

from utils.process_log import(
    process_logs_from_s3
)

from os import path
from halo import Halo

from dotenv import load_dotenv
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv('aws_access_key')
AWS_SECRET_ACCESS_KEY = os.getenv('aws_secret_key')
AWS_DEFAULT_REGION = os.getenv('aws_region')
SQS_URL = os.getenv('SQS_URL') # aws standard url 
SNS_TOPIC = os.getenv('SNS_TOPIC') # aws sns
DLQ_URL = os.getenv('DLQ_URL') # dead letter queue url

# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')






def import_config_from_yaml(configfile:str) -> Config:
    """
    Read yaml and 
    :param configfile: config file name
    :return: Config obj.
    """
    try:
        config_params_obj = Config.import_config_from_yaml(f"./config/{configfile}")
    except Exception as e:
        raise Exception(f"Impor Config Rrror {e}")
    return config_params_obj


def run_process_files(number,delete_nodes,configfile):
    """
    Proccess files in S3 bucket
    :param number: number of first n files in bucket
    :param delete_nodes: delete node after process files
    :param configfile: config file name
    """
    # check aws credential
     
    try:
        check_aws_validity(key_id=AWS_ACCESS_KEY_ID, secret=AWS_SECRET_ACCESS_KEY)
    except Exception as e:
        logger.error("AWS credential failed")
        return 
    #convert yaml and aws credentials to json and pass into kubernetes
    try:
        solardata_parmas_obj = SolarParams.import_solar_params_from_yaml(f"./config/{configfile}")
        config_params_obj = Config.import_config_from_yaml(f"./config/{configfile}",                                                     aws_access_key=AWS_ACCESS_KEY_ID,
                                                            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                                            aws_region=AWS_DEFAULT_REGION,
                                                            sns_topic=SNS_TOPIC)
    except Exception as e:

        logger.error(f" ================================== ERROR ========================================= ")
        logger.error(f" ========= Could not find {configfile} {e}========================================= ")
        logger.error   ("======== Apply ./config/config.yaml file instead ================================ ")
        logger.error(f" ================================================================================== ")
        solardata_parmas_obj = SolarParams.import_solar_params_from_yaml(f"./config/config.yaml")
        config_params_obj = Config.import_config_from_yaml(file = f"./config/config.yaml",
                                                            aws_access_key=AWS_ACCESS_KEY_ID,
                                                            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                                            aws_region=AWS_DEFAULT_REGION,
                                                            sns_topic=SNS_TOPIC)

    # step 1 . check node status from local or AWS
    # spinner = Halo(text='Loading', spinner='dots')

    if config_params_obj.environment == "AWS":
        logger.info(" ============ Running on AWS ===============")
        config_params_obj.container_type = "kubernetes"
        config_params_obj.container_name = "webapp"
        scale_nodes_and_wait(scale_node_num=int(config_params_obj.eks_nodes_number), counter=int(config_params_obj.scale_eks_nodes_wait_time), delay=1, config_params_obj = config_params_obj)
        # create or update k8s setting based on yaml files
        try:
            create_or_update_k8s(config_params_obj=config_params_obj,env="aws")
        except Exception as e:
            logger.error(f"Create or update k8s error :{e}")
            return 

    else:
        # local env
        if config_params_obj.container_type == "kubernetes":
            # check if k8s and webapp exist
            try:
                create_or_update_k8s(config_params_obj=config_params_obj,env="local")
            except Exception as e:
                logger.error(f"Create or update k8s error :{e}")
                return 

    # # # step 2 . clear sqs
    logger.info(" ========= Clean previous SQS ========= ")
    sqs_client = connect_aws_client(client_name='sqs',
                                    key_id=AWS_ACCESS_KEY_ID, 
                                    secret=AWS_SECRET_ACCESS_KEY,
                                    region=AWS_DEFAULT_REGION)
    clean_previous_sqs_message(sqs_url=SQS_URL, sqs_client=sqs_client, wait_time=2, counter=60, delay=1)

    total_task_num = 0
    if number is None:
        logger.info(" ========= Process default files in config.yam ========= ")  
        try:
            res = invoke_docekr_exec_run_process_files(config_obj = config_params_obj,
                                            solarParams_obj= solardata_parmas_obj,
                                            container_type= config_params_obj.container_type, 
                                            container_name=config_params_obj.container_name)
            total_task_num = len(config_params_obj.files) + 1
        except Exception as e:
            logger.error(f"Process default files failed :{e}")
            return 
    else:
        if type(int(number)) == int:
            total_task_num = 0
            if int(number) == 0 :
                all_files = list_files_in_bucket(bucket_name=config_params_obj.bucket,key_id=AWS_ACCESS_KEY_ID, secret_key=AWS_SECRET_ACCESS_KEY,aws_region=AWS_DEFAULT_REGION)
                number_files = len(all_files)
                total_task_num = len(all_files) + 1
                logger.info(f" ========= Process all {number_files} files in bucket ========= ")
            else :
                logger.info(f" ========= Process first {number} files in bucket ========= ")
                total_task_num = int(number) + 1
            try:
                res = invoke_docekr_exec_run_process_first_n_files( config_params_obj,solardata_parmas_obj, number, config_params_obj.container_type, config_params_obj.container_name)
           
            except Exception as e:
                logger.error(f"Process first {number} files failed :{e}")
                return   
           
        else:
            print(f"error input {number}")
            return 
    # log pulling 
    thread = taskThread(threadID=1,
                        name="sqs",
                        counter=120, 
                        wait_time=2 ,
                        sqs_url=SQS_URL,
                        num_task=total_task_num, 
                        config_params_obj=config_params_obj,
                        delete_nodes_after_processing=delete_nodes, 
                        dlq_url=DLQ_URL,
                        key_id=AWS_ACCESS_KEY_ID,
                        secret_key=AWS_SECRET_ACCESS_KEY,
                        aws_region=AWS_DEFAULT_REGION
                        )
    thread.start()
    return 






def check_nodes_status():
    """
    Check EKS node status
    """
    config.load_kube_config()
    v1 = client.CoreV1Api()
    response = v1.list_node()
    nodes = []
    # check confition
    for node in response.items:
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
            logger.info(f"{hostname} is not ready status:{status}")
            return False
    for node in nodes:
        logger.info(f"{node.hostname} is ready")
    return True



def process_logs_and_plot():
    config_params_obj = Config.import_config_from_yaml("./config/config.yaml")
    s3_client = connect_aws_client(client_name="s3",key_id=AWS_ACCESS_KEY_ID, 
                                    secret=AWS_SECRET_ACCESS_KEY,
                                    region=AWS_DEFAULT_REGION)


    logs_full_path_name = config_params_obj.saved_logs_target_path + "/" + config_params_obj.saved_logs_target_filename
    process_logs_from_s3(config_params_obj.saved_bucket, logs_full_path_name, "results/runtime.png", s3_client)

def print_dlq(empty):
    logger.info("Read DLQ")
    sqs_client = connect_aws_client(client_name='sqs',
                                    key_id=AWS_ACCESS_KEY_ID, 
                                    secret=AWS_SECRET_ACCESS_KEY,
                                    region=AWS_DEFAULT_REGION)
    counter = 60
    while counter:
        messages = receive_queue_message(queue_url=DLQ_URL,MaxNumberOfMessages=1 ,sqs_client=sqs_client, wait_time=1)
        if 'Messages' in messages:
            for msg in messages['Messages']:
                msg_body = msg['Body']
                receipt_handle = msg['ReceiptHandle']
                message_id = msg['MessageId']
                logger.info(f'The message body: {msg_body}')

                # logger.info('Deleting message from the queue...')
                if empty:
                    delete_queue_message(DLQ_URL, receipt_handle, sqs_client)

                logger.info(f'Received and deleted message(s) from {DLQ_URL}.')
                print(receipt_handle)
        else:
            logger.info("Clean DLQ message completed")
            return

        counter -= 1
        time.sleep(1)



# Parent Command
@click.group()
def main():

	pass

# Run files 
@main.command()
@click.option('--number','-n',
            help="Process the first n files in bucket, if number=0, run all files in the bucket", 
            default= None)
@click.option('--deletenodes','-delete',
            help="Enbale or disable delet nodes after process, default is Ture. Set False to disable ", 
            default= True)
@click.option('--configfile','-f',
            help="Assign config files, Default files is config.yaml under /config" , 
            default= "config.yaml")

def run_files(number,deletenodes, configfile):
    """ Run Process Files"""
    run_process_files(number, deletenodes,configfile)

@main.command()
@click.argument('min_nodes')
@click.option('--configfile','-f',
            help="Assign config files, Default files is config.yaml under /config" , 
            default= "config.yaml")
def nodes_scale(min_nodes,configfile):
    """Increate or decrease nodes number"""
    logger.info(f"Scale nodes {min_nodes}")
    try:
        config_obj = import_config_from_yaml(configfile)
    except Exception as e:
        return logger.error(e)
    scale_nodes_and_wait(scale_node_num=min_nodes, counter=80,delay=1,config_params_obj=config_obj)


@main.command()
def check_nodes():
    """ Check nodes status """
    check_nodes_status()


@main.command()
def processlogs():
    """"Try logs"""
    process_logs_and_plot()

@main.command()
@click.option('--empty','-e',
            help=" Empty DLQ after receive message", 
            default= False)
def read_dlq(empty):
    """Increate or decrease nodes number"""
    print_dlq(empty)


if __name__ == '__main__':
	main()