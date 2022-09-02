import logging
from .invoke_function import exec_eksctl_create_cluster,exec_eksctl_delete_cluster
from .modiy_config_parameters import modiy_config_parameters,convert_yaml_to_json
from .create_ec2 import check_if_ec2_ready_for_ssh,run_command_in_ec2_ssh,upload_file_to_sc2
from os.path import exists
import boto3
import os
from .check_aws import (
    connect_aws_client,
    check_environment_is_aws,
    connect_aws_resource,
)
# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def handle_eks_cluster_action(
    config_file:str, 
    aws_access_key:str,
    aws_secret_access_key:str, 
    aws_region:str,
    action:str
)-> str:

    

    s3_client = connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )

    config_json = modiy_config_parameters(
            configfile=config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_client= s3_client,
        )


    ec2_client = connect_aws_client(
        client_name="ec2",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )


    ec2_bastion_saved_config_file  = config_json['aws_config']['ec2_bastion_saved_config_file']
    cluster_file = config_json['aws_config']['cluster_file']
    # # ec2_config_yaml = f"./config/{configfile}"

    if exists(ec2_bastion_saved_config_file) is False:
        logger.error(
            f"{ec2_bastion_saved_config_file} not exist, use default config.yaml instead"
        )
        return 


    ec2_json = convert_yaml_to_json(yaml_file=ec2_bastion_saved_config_file)
    key_pair_name = ec2_json['key_pair_name']
    pem_location = ec2_json['pem_location']
    ec2_instance_id = ec2_json['ec2_instance_id']
    action = action.upper()
    pem_file=pem_location +"/"+key_pair_name+".pem"
    user_name = ec2_json['user_name']
    remote_base_path = f"/home/{user_name}/gismo-cloud-deploy/gismoclouddeploy/services"


    if pem_location is None or os.path.exists(pem_location) is None: 
        logger.error(f"{pem_location} does not exist")
        return 
    
    if key_pair_name is None:
        logger.error(f"{key_pair_name} does not exist. Please create key pair first")
        return 

    if check_environment_is_aws():
        # 
        logger.info("On AWS ")
        if action == "CREATE":
            logger.info("Create cluster on AWS EC2")
            create_eks_cluster(
                cluster_file= cluster_file
            )
        elif action == "DELETE":
            logger.info("Delete cluster on AWS EC2")
            delete_eks_cluster(cluster_file=cluster_file)
        else:
            logger.error(f"unknow action: {action} ")

        return 
    else:
        # check ec2 bastion

        try:
            response = ec2_client.describe_instance_status(InstanceIds=[ec2_instance_id], IncludeAllInstances=True)
            state = response['InstanceStatuses'][0]['InstanceState']['Name']
            logger.info(f"Current instance satate: {state}")
            if state == 'stopped':
                logger.info(f"EC2 instance: {ec2_instance_id} is stopped. Start instance")
                ec2 = boto3.resource('ec2')
                res = ec2.instances.filter(InstanceIds = [ec2_instance_id]).start() #for start an ec2 instance
                instance = check_if_ec2_ready_for_ssh(instance_id=ec2_instance_id, wait_time=60, delay=5, pem_location=pem_file,user_name=user_name)

            # upload cluster file to EC2 bastion 

  
            # upload .env
            local_env = cluster_file
            localpath , file = os.path.split(cluster_file)
            remote_env=f"{remote_base_path}/config/eks/{file}"
            logger.info("-------------------")
            logger.info(f"upload local {local_env} to {remote_env}")
            logger.info("-------------------")

            upload_file_to_sc2(
                user_name="ec2-user",
                instance_id=ec2_instance_id,
                pem_location=pem_file,
                ec2_client=ec2_client,
                local_file=local_env,
                remote_file=remote_env,
            )


            if action == "CREATE":
                logger.info("Create cluster through SSH from local")
                command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl create cluster -f {remote_env}"
               
            elif action == "DELETE":
                logger.info("Delete cluster throuth SSH from local")
                command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl delete cluster -f {remote_env}"

            elif action == "LIST":
                logger.info("List all eks cluster")
                command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl get cluster"

            elif action == "SCALEZERO":
                logger.info("Scale to zero")
                cluster_dict = convert_yaml_to_json(yaml_file=cluster_file)
                cluster_name = cluster_dict['metadata']['name']
                if len (cluster_dict['nodeGroups']) == 0 :
                    logger.error("nodeGroup does not defined")
                    return 
                group_name = cluster_dict['nodeGroups'][0]['name']
                command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl scale nodegroup --cluster {cluster_name} --name {group_name} --nodes 0"
 
            elif action =="GETNODES":
                logger.info("Get node")

            elif action =="GETALL":
                logger.info("Get all in all namespace - kubectl get all --all-namespaces ")
                command = f"kubectl get all --all-namespaces"
            else:
                logger.error(f"unknow action: {action} ")
                return 

            run_command_in_ec2_ssh(
                    user_name=user_name,
                    instance_id=ec2_instance_id,
                    command=command,
                    pem_location=pem_file,
                    ec2_client=ec2_client
             )

        except Exception :
            logger.error(f"Cannot find instance id{ec2_instance_id} or not in a state to start instance.")
            raise Exception 

        return 




def create_eks_cluster(cluster_file:str) -> str:

    if not exists(cluster_file):
        logger.error(f"{cluster_file} does not exist")
        return 
    res = exec_eksctl_create_cluster(cluster_file=cluster_file)
    logger.info(res)
    return 


def delete_eks_cluster(cluster_file:str) -> str:
    if not exists(cluster_file):
        logger.error(f"{cluster_file} does not exist")
        return 
    res = exec_eksctl_delete_cluster(cluster_file=cluster_file)
    logger.info(res)
    return 