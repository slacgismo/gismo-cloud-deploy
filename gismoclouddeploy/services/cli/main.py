
import click


import logging

import click
from models.Node import Node
from kubernetes import client, config

import os
from utils.InvokeFunction import (
    invok_docekr_exec_run_process_files,
    invok_docekr_exec_run_process_all_files,
    invok_docekr_exec_run_process_first_n_files,
    )
from models.SolarParams import SolarParams
from models.Config import Config


from utils.aws_utils import (
    connect_aws_client
)

from utils.eks_utils import(
    scale_node_number,
    scale_nodes_and_wait,

    create_or_update_k8s
)

from utils.taskThread import (
    taskThread,
)

from utils.aws_utils import (
    check_environment_is_aws,
    list_files_in_bucket
)

from utils.sqs import(

    clean_previous_sqs_message,
)

from utils.process_log import(
    process_logs_from_s3
)

from os import path
from halo import Halo

# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')

from dotenv import load_dotenv
load_dotenv()

SQS_URL = os.getenv('SQS_URL')
SQS_ARN = os.getenv('SQS_ARN')
SNS_TOPIC = os.getenv('SNS_TOPIC')




def run_process_files(number,delete_nodes):
    # import parametes from yaml
    solardata_parmas_obj = SolarParams.import_solar_params_from_yaml("./config/config.yaml")
    config_params_obj = Config.import_config_from_yaml("./config/config.yaml")
    # step 1 . check node status from local or AWS
    # spinner = Halo(text='Loading', spinner='dots')

    if check_environment_is_aws():
        config_params_obj.container_type = "kubernetes"
        config_params_obj.container_name = "webapp"
        scale_nodes_and_wait(scale_node_num=int(config_params_obj.eks_nodes_number), counter=int(config_params_obj.scale_eks_nodes_wait_time), delay=1)
        # create or update k8s setting based on yaml files
        create_or_update_k8s(config_params_obj=config_params_obj,env="aws")

    else:
        # local 
        if config_params_obj.container_type == "kubernetes":
            # check webapp exist
            create_or_update_k8s(config_params_obj=config_params_obj,env="local")
            
    # # # step 2 . clear sqs
    logger.info(" ========= Clean previous SQS ========= ")
    sqs_client = connect_aws_client('sqs')
    clean_previous_sqs_message(sqs_url=SQS_URL, sqs_client=sqs_client, wait_time=2)

    total_task_num = 0
    if number == 'f':
        logger.info(" ========= Process default files in config.yam ========= ")  

        res = invok_docekr_exec_run_process_files(config_obj = config_params_obj,
                                        solarParams_obj= solardata_parmas_obj,
                                        container_type= config_params_obj.container_type, 
                                        container_name=config_params_obj.container_name)
        total_task_num = len(config_params_obj.files) + 1
    elif number == "n":
        all_files = list_files_in_bucket(config_params_obj.bucket)
        number_files = len(all_files)
        logger.info(f" ========= Process all {number_files} files in bucket ========= ")
        res = invok_docekr_exec_run_process_all_files( config_params_obj,solardata_parmas_obj, config_params_obj.container_type, config_params_obj.container_name)
        total_task_num = len(all_files) + 1

    else:
        if type(int(number)) == int:
            logger.info(f" ========= Process first {number} files in bucket ========= ")
            res = invok_docekr_exec_run_process_first_n_files( config_params_obj,solardata_parmas_obj, number, config_params_obj.container_type, config_params_obj.container_name)
            total_task_num = int(number) + 1
           
        else:
            print(f"error input {number}")
            return 
    # log pulling 
    thread = taskThread(1,"sqs",120, 2 ,SQS_URL,total_task_num, config_params_obj=config_params_obj, delete_nodes_after_processing=delete_nodes)
    thread.start()
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



def process_logs_and_plot():
    config_params_obj = Config.import_config_from_yaml("./config/config.yaml")
    s3_client = connect_aws_client("s3")
    logs_full_path_name = config_params_obj.saved_logs_target_path + "/" + config_params_obj.saved_logs_target_filename
    process_logs_from_s3(config_params_obj.saved_bucket, logs_full_path_name, "results/runtime.png", s3_client)


# Parent Command
@click.group()
def main():
	pass



# Run files 
@main.command()
@click.option('--number','-n',
            help="Process the first n files in bucket, if number=n, run all files in the bucket", 
            default= None)
@click.option('--deletenodes','-delete',
            help="Process the first n files in bucket, if number=n, run all files in the bucket", 
            default= True)
def run_files(number,deletenodes):
    """ Run Process Files"""
    run_process_files(number, deletenodes)

@main.command()
@click.argument('min_nodes')
def nodes_scale(min_nodes):
    """Increate or decrease nodes number"""
    scale_node_number(min_nodes)

@main.command()
def check_nodes():
    """ Check nodes status """
    check_nodes_status()


@main.command()
def processlogs():
    """"Try logs"""
    process_logs_and_plot()



if __name__ == '__main__':
	main()