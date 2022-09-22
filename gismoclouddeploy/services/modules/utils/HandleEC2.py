
import readline
from os.path import relpath
from os.path import normpath, basename
from pathlib import Path
from os.path import exists
import time

from .SSHAction import SSHAction
from .command_utils import verify_keys_in_configfile
import re
import socket

from .handle_inputs import (
    handle_yes_or_no_question,
    handle_input_s3_bucket_question,
    handle_input_number_of_process_files_question,
    handle_input_number_of_scale_instances_question,
    hanlde_input_project_name_in_tag,
    handle_input_project_path_question,
    select_is_breaking_ssh
)

from transitions import Machine
import os
import coloredlogs, logging
from terminaltables import AsciiTable
import inquirer
from .EC2Action import EC2Action
from .EKSAction import EKSAction
from .modiy_config_parameters import convert_yaml_to_json
from .check_aws import (
    connect_aws_client,
    check_environment_is_aws,
    connect_aws_resource,
    check_bucket_exists_on_s3,
    get_security_group_id_with_name,
    check_keypair_exist,
    get_default_vpc_id,
    get_ec2_instance_id_and_keypair_with_tags,
    get_ec2_state_from_id,
    check_vpc_id_exists,
    check_sg_group_name_exists_and_return_sg_id,
    get_iam_user_name,
    check_keypair_name_exists
    
)
from .create_ec2 import (
    create_security_group,
    create_key_pair,
    create_instance,
    check_if_ec2_ready_for_ssh,
    get_public_ip,
    upload_file_to_sc2,
    run_command_in_ec2_ssh,
    write_aws_setting_to_yaml,
    ssh_upload_folder_to_ec2,
    get_all_files_in_local_dir,
    ssh_download_folder_from_ec2,
    
    
)
from .EKSAction import EKSAction
coloredlogs.install()

class HandleEC2(object):

    def __init__(
            self, 
            export_full_path_name:str = None,
            aws_access_key: str = None,
            aws_secret_access_key: str = None,
            aws_region: str = None,
            securitygroup_ids:list = [],
            ec2_image_id:str = None,
            ec2_instance_id:str = None,
            ec2_instance_type:str = None,
            ec2_volume :str = None, 
            key_pair_name:str = None,
            pem_file_path:str = None,
            login_user:str = None,
            vpc_id:str = None,
            tags:list = [],
            ssh_total_wait_time: int = 90,
            ssh_wait_time_interval:int = 1,
        ) -> None:
        self.export_config_path = export_full_path_name
        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region

        self.securitygroup_ids = securitygroup_ids
        self.ec2_image_id = ec2_image_id
        self.ec2_instance_id = ec2_instance_id
        self.ec2_instance_type = ec2_instance_type
        self.ec2_volume = ec2_volume
        self.key_pair_name = key_pair_name
        self.login_user = login_user
        self.tags = tags
        self._ec2_action = None
        self.vpc_id = vpc_id
        self.pem_file_path = pem_file_path

        self._ec2_client  = connect_aws_client(
            client_name='ec2',
            key_id= self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        self._ec2_resource  = connect_aws_resource(
            resource_name='ec2',
            key_id= self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        self._ec2_public_ip = None
        self._ec2_status = None
        self._ssh_total_wait_time = ssh_total_wait_time
        self._ssh_wait_time_interval = ssh_wait_time_interval
        
    def export_parameters_to_file(self):
        config_dict  = {}
        config_dict['SecurityGroupIds'] = self.securitygroup_ids
        config_dict['ec2_image_id'] = self.ec2_image_id
        config_dict['ec2_instance_id'] = self.ec2_instance_id
        config_dict['ec2_instance_type'] = self.ec2_instance_type
        config_dict['ec2_volume'] = self.ec2_volume
        config_dict['key_pair_name'] = self.key_pair_name
        config_dict['login_user'] = self.login_user
        config_dict['tags'] = self.tags
        config_dict['vpc_id'] = self.vpc_id
        
        write_aws_setting_to_yaml(
                file=self.export_config_path, 
                setting=config_dict
            )
        logging.info("Export eks config")


    def get_pem_file_full_path_name(self):
        print(f"self.pem_file_path :{self.pem_file_path}")
        full_path = self.pem_file_path +f"/{self.key_pair_name}.pem"
        return full_path


    def set_ec2_action(self, action):
        self._ec2_action = action
    
    def get_ec2_action(self, action):
        return self._ec2_action


    def get_public_ip(self):
        instance = check_if_ec2_ready_for_ssh(
            instance_id=self._ec2_instance_id , 
            wait_time=self._ssh_total_wait_time, 
            delay=self._ssh_wait_time_interval, 
            pem_location=self.get_pem_file_full_path_name(),
            user_name=self.login_user)

        logging.info(f"instance ready :{instance}")

        self._ec2_public_ip = get_public_ip(
            ec2_client=self._ec2_client,
            instance_id=self._ec2_instance_id
        )
        logging.info("---------------------")
        logging.info(f"public_ip :{self._ec2_public_ip}")
        logging.info("---------------------")
        return self._ec2_public_ip



    def get_ec2_status(self):
        if self.ec2_instance_id is None:
            raise Exception("EC2 id does not exist")
        self._ec2_status = get_ec2_state_from_id(
            ec2_client=self._ec2_client,
            id=self.ec2_instance_id
        )

        return self._ec2_status

    def ssh_update_eks_cluster_file(self, local_cluster,saved_config_folder_name ):
        remote_cluster = f"/home/{self.login_user}/gismo-cloud-deploy/gismoclouddeploy/services/projects/{saved_config_folder_name}/cluster.yaml"
        
        upload_file_to_sc2(
            user_name=self.login_user,
            instance_id=self.ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self.ec2_instance_id,
            local_file=local_cluster,
            remote_file=remote_cluster,
        )
    def ssh_update_eks_cluster_file_to_project_folder(self, local_cluster,project_folder_anme ):
        remote_cluster = f"/home/{self.login_user}/gismo-cloud-deploy/gismoclouddeploy/services/projects/{project_folder_anme}/cluster.yaml"
        
        upload_file_to_sc2(
            user_name=self.login_user,
            instance_id=self.ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self.ec2_instance_id,
            local_file=local_cluster,
            remote_file=remote_cluster,
        )

    def ssh_upload_folder(self, local_project_path, relative_project_folder_name):
        remote_projects_path = f"/home/{self.login_user}/gismo-cloud-deploy/gismoclouddeploy/services/projects"
        is_update_folder = handle_yes_or_no_question(
            input_question="Do you want to update(upload) project folder?",
            default_answer="yes"
        )
        print(f"is_update_folder :{is_update_folder}")
        print(f"local_project_path {local_project_path} remote_projects_path {remote_projects_path}")
        if is_update_folder is True:
            ssh_upload_folder_to_ec2(
                user_name=self.login_user,
                instance_id=self.ec2_instance_id,
                pem_location=self.get_pem_file_full_path_name(),
                local_folder=local_project_path,
                remote_folder=remote_projects_path,
                ec2_resource=self._ec2_resource,

            )

    def input_is_breaking_ssh(self):
        is_breaking = select_is_breaking_ssh()
        return is_breaking

    def handle_input_ssh_custom_command(self):

        custom_command = input(f"Please type your command: ")
        return custom_command


    def run_ssh_command(self, ssh_command:str):
        remote_base_path = f"/home/{self.login_user}/gismo-cloud-deploy/gismoclouddeploy/services/"
        full_ssh_command = f"cd {remote_base_path} \n source ./venv/bin/activate \n {ssh_command} "
        pem_file_full_path_name = self.get_pem_file_full_path_name()
        run_command_in_ec2_ssh(
            user_name= self.login_user,
            instance_id= self.ec2_instance_id,
            pem_location=pem_file_full_path_name,
            ec2_client=self._ec2_client,
            command=full_ssh_command
        )


    def ec2_ssh_installation(self, local_project_path:str):
        logging.info("Handle install dependencies")
        instance = check_if_ec2_ready_for_ssh(
            instance_id=self.ec2_instance_id , 
            wait_time=self._ssh_total_wait_time, 
            delay=self._ssh_wait_time_interval, 
            pem_location=self.get_pem_file_full_path_name(),
            user_name=self.login_user)

        logging.info(f"instance ready :{instance}")

        self._ec2_public_ip = get_public_ip(
            ec2_client=self._ec2_client,
            instance_id=self.ec2_instance_id
        )
        logging.info("---------------------")
        logging.info(f"public_ip :{self._ec2_public_ip}")
        logging.info("---------------------")
        # upload install.sh
        logging.info("-------------------")
        logging.info(f"upload install.sh")
        logging.info("-------------------")
        # upload .env
        local_env = "./config/deploy/install.sh"
        remote_env="/home/ec2-user/install.sh"
        upload_file_to_sc2(
            user_name=self.login_user,
            instance_id=self.ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self._ec2_client,
            local_file=local_env,
            remote_file=remote_env,
        )
        # run install.sh
        logging.info("=============================")
        logging.info("Run install.sh ")
        logging.info("=============================")
        command = f"bash /home/ec2-user/install.sh"
        run_command_in_ec2_ssh(
            user_name=self.login_user,
            instance_id=self.ec2_instance_id,
            command=command,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self._ec2_client
        )

        remote_base_path = f"/home/{self.login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
        # upload .env
        logging.info("-------------------")
        logging.info(f"upload .env")
        logging.info("-------------------")
        # upload .env
        local_env = ".env"
        
        remote_env=f"{remote_base_path}/.env"
        upload_file_to_sc2(
            user_name=self.login_user,
            instance_id=self.ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self._ec2_client,
            local_file=local_env,
            remote_file=remote_env,
        )

        logging.info("-------------------")
        logging.info(f"Set up aws cli credentials ")
        logging.info("-------------------")
        ssh_command = f"aws configure set aws_access_key_id {self.aws_access_key} \n aws configure set aws_secret_access_key {self.aws_secret_access_key} \n aws configure set default.region {self.aws_region}"
        run_command_in_ec2_ssh(
            user_name= self.login_user,
            instance_id= self.ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self._ec2_client,
            command=ssh_command
        )
    
        remote_projects_folder = remote_base_path + f"/projects"
        
        logging.info("-------------------")
        logging.info(f"upload local project folder to ec2 projects")
        logging.info(f"local folder:{local_project_path}")
        logging.info(f"remote folder:{remote_projects_folder}")
        logging.info("-------------------")
        
        

        ssh_upload_folder_to_ec2(
            user_name=self.login_user,
            instance_id=self.ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            local_folder=local_project_path,
            remote_folder=remote_projects_folder,
            ec2_resource=self._ec2_resource,

        )






    def handle_ec2_action(self):

        if self._ec2_action == EC2Action.create.name:
            logging.info("Create new EC2 instances")
            try:
                ec2_instance_id = create_instance(     
                    ImageId=self.ec2_image_id,
                    InstanceType = self.ec2_instance_type,
                    key_piar_name = self.key_pair_name,
                    ec2_client=self._ec2_client,
                    tags= self.tags,
                    SecurityGroupIds = self.securitygroup_ids,
                    volume=self.ec2_volume

                )
                logging.info(f"ec2_instance_id: {ec2_instance_id}")
                self.ec2_instance_id = ec2_instance_id
                logging.info("-------------------")
                logging.info(f"Create ec2 bastion completed")
                logging.info("-------------------")

            except Exception as e:
                raise Exception(f"Create ec2 instance failed {e}")
        elif self._ec2_action == EC2Action.start.name:
            if self.ec2_instance_id is not None:
                res = self._ec2_resource.instances.filter(InstanceIds = [self.ec2_instance_id]).start() #for stopping an ec2 instance
                instance = check_if_ec2_ready_for_ssh(instance_id=self.ec2_instance_id, wait_time=self._ssh_total_wait_time, delay=self._ssh_wait_time_interval, pem_location=self.get_pem_file_full_path_name(),user_name=self.login_user)
                self._ec2_public_ip = get_public_ip(
                    ec2_client=self._ec2_client,
                    instance_id=self.ec2_instance_id
                )
                logging.info("---------------------")
                logging.info(f"public_ip :{self._ec2_public_ip}")
                logging.info("---------------------")
                logging.info("Ec2 start")
                
        elif self._ec2_action == EC2Action.stop.name:
            if self.ec2_instance_id is not None:
                res = self._ec2_resource.instances.filter(InstanceIds = [self.ec2_instance_id]).stop() #for stopping an ec2 instance
            else:
                logging.error("ec2_resource id is empty")
            return
        elif self._ec2_action == EC2Action.terminate.name:
            logging.info("Get ec2 terminate")
            if self.ec2_instance_id is not None:
                # res = self._ec2_resource.instances.filter(InstanceIds = [self.ec2_instance_id]).stop() #for stopping an ec2 instance
                res_term  = self._ec2_resource.instances.filter(InstanceIds = [self.ec2_instance_id]).terminate() #for terminate an ec2 insta
            else:
                logging.error("ec2_resource id is empty")
            return

    def handle_ssh_eks_action(
        self,
        eks_action:str , 
        cluster_file:str = None,
        # relative_project_folder_name:str = None,
        relative_saved_config_folder_name: str = None

        ):

        remote_base_path = f"/home/{self.login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
        # remote_projects_path = f"/home/{self.login_user}/gismo-cloud-deploy/gismoclouddeploy/services/projects/{relative_project_folder_name}"
        remote_cluster_file = remote_base_path  +f"/projects/{relative_saved_config_folder_name}/cluster.yaml"


        cluster_config_dict = convert_yaml_to_json(yaml_file=cluster_file)  
        cluster_name = cluster_config_dict['metadata']['name']
        nodegroup_name = cluster_config_dict['nodeGroups'][0]['name']
# 
        ssh_command_list = {}
        if eks_action == EKSAction.create.name:
            logging.info("SSH create eks")
            command = f"eksctl create cluster -f {remote_cluster_file}"
            ssh_command_list['Create EKS cluster'] = command

        elif eks_action == EKSAction.delete.name:
            logging.info("set delete eks culster command ")
            # scale down if cluster exist
            scaledown_command =  f"rec=\"$(eksctl get cluster | grep {cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl scale nodegroup --cluster {cluster_name} --name {nodegroup_name} --nodes 0; fi"
            ssh_command_list['scaledonw cluster'] = scaledown_command
            # delete cluster if cluster exist
            delete_eks_command =  f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n rec=\"$(eksctl get cluster | grep {cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl delete cluster -f {remote_cluster_file}; fi"
            # delete_eks_command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl delete cluster -f {remote_cluster_file}"
            ssh_command_list['Delete EKS cluster'] = delete_eks_command

        elif eks_action == EKSAction.list.name:
            logging.info("Run list eks")
            command = f"eksctl get cluster"
            ssh_command_list['List EKS cluster'] = command

        elif eks_action == EKSAction.scaledownzero.name:
            logging.info("SSH scale down zero eks")
            scale_down_command = f"rec=\"$(eksctl get cluster | grep {cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl scale nodegroup --cluster {cluster_name} --name {nodegroup_name} --nodes 0; fi"

        for description, command in ssh_command_list.items():
            logging.info(description)
            run_command_in_ec2_ssh(
                    user_name=self.login_user,
                    instance_id=self.ec2_instance_id,
                    command=command,
                    pem_location=self.get_pem_file_full_path_name(),
                    ec2_client=self._ec2_client
             )
    def hande_input_is_cleanup(self):
        is_clean_up = handle_yes_or_no_question(
            input_question="Do you want to delete all created resources?\nIf you type 'no', there will be an operating cost from generated eks cluster (You pay $0.10 per hour for each Amazon EKS cluster that you create.Sept,2022). The ec2 bastion will be stopped (no operating cost).\nHowever, if you type 'yes', the generated ec2 bastions and eks cluster will be deleted (No operating cost from ec2 and eks cluster).\n It takes about 10~20 mins to generated a new eks cluster.\n ",
            default_answer="no"
        )

        return is_clean_up
        
    def ssh_download_results(self, local_project_path, remote_results_path):
        ssh_download_folder_from_ec2(
            user_name=self.login_user,
            instance_id=self.ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self.ec2_instance_id,
            local_file=local_project_path,
            remote_file=remote_results_path,
        )

def create_ec2_object_from_dict(
    saved_ec2_config_file:str,
    aws_access_key:str, 
    aws_secret_access_key:str,
    aws_region:str,
    pem_file_path:str,
    ) -> HandleEC2:

    ec2_config = convert_yaml_to_json(
        yaml_file=saved_ec2_config_file
    )
    securitygroup_ids  = ec2_config['SecurityGroupIds']
    ec2_image_id = ec2_config['ec2_image_id']
    ec2_instance_id = ec2_config['ec2_instance_id']
    ec2_instance_type = ec2_config['ec2_instance_type']
    ec2_volume = ec2_config['ec2_volume']
    key_pair_name = ec2_config['key_pair_name']
    login_user = ec2_config['login_user']
    tags = ec2_config['tags']
    vpc_id = ec2_config['vpc_id']




    _handle_ec2 = HandleEC2(
        export_full_path_name=saved_ec2_config_file,
        aws_access_key=aws_access_key,
        aws_secret_access_key = aws_secret_access_key,
        aws_region =aws_region,
        securitygroup_ids=securitygroup_ids,
        ec2_image_id=ec2_image_id,
        ec2_instance_id=ec2_instance_id,
        ec2_instance_type=ec2_instance_type,
        ec2_volume=ec2_volume,
        key_pair_name=key_pair_name,
        vpc_id = vpc_id,
        login_user=login_user,
        tags=tags,
        pem_file_path = pem_file_path

    )

    return _handle_ec2

