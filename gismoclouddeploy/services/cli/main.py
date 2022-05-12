
from email.policy import default
import click
from models.Node import Node
from concurrent.futures import thread
from distutils.command.config import config
import json
from kubernetes import client, config
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

from multiprocessing.pool import ThreadPool as Pool
from threading import Timer
import asyncio
from models.SolarParams import SolarParams
from models.Config import Config
from models.Task import Task



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
def check_nodes_status():
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



def scale_node_number(min_nodes):
    # check if input is integer
    # assert(type(min_nodes) is int, f"Input {min_nodes} is not an")
    try: 
        node = int(min_nodes)
    except Exception as e:
        print(f"Error: input {min_nodes} is not a integer")
        return False

    # return if running in AWS
    if check_environment() != True:
        return False
    if int(min_nodes) == 0 :
     
        res = invoke_eksctl_scale_node(cluster_name="gcd-eks-cluster",
                                        group_name="gcd-node-group-lt",
                                        nodes=0,
                                        nodes_max=1,
                                        nodes_min=0)
        print(f"scale down to {min_nodes}, res: {res}")
    else:
        res = invoke_eksctl_scale_node(cluster_name="gcd-eks-cluster",
                                        group_name="gcd-node-group-lt",
                                        nodes=min_nodes,
                                        nodes_max=min_nodes,
                                        nodes_min=min_nodes)
        print(f"scale up to {min_nodes}, res:{res}")
        # check node status
        # check_nodes_status()
    

def check_environment():
    my_user = os.environ.get("USER")
    is_aws = True if "ec2" in my_user else False
    return is_aws

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
@click.argument('text')
def capitalize(text):
	"""Capitalize Text"""
	click.echo(text.upper())



if __name__ == '__main__':
	main()