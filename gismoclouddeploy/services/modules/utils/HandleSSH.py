
from glob import escape
import readline
from os.path import relpath
from os.path import normpath, basename
from pathlib import Path
from os.path import exists
import time
from .command_utils import verify_keys_in_configfile
import re
import socket

from .handle_inputs import (
    handle_yes_or_no_question,
    handle_input_s3_bucket_question,
    handle_input_number_of_process_files_question,
    handle_input_number_of_scale_instances_question,
    hanlde_input_project_name_in_tag,
    handle_input_project_path_question
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
    
    
)
from .EKSAction import EKSAction
coloredlogs.install()
from .AWSActions import AWSActions

class HandleSSH(object):
    def __init__(
            self, 
            keypair_name:str = None,
            local_pem_path:str = None,
            aws_access_key: str = None,
            aws_secret_access_key: str = None,
            aws_region: str = None,
            ec2_instance_id: str = None,
            ssh_total_wait_time:int = 60,
            login_user:str = None,
            local_project_path :str = None

        ) -> None:
        self.aws_access_key =aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region= aws_region
        self.local_pem_path = local_pem_path,
        self.keypair_name = keypair_name
        self._pem_full_path_name = self.local_pem_path +f"/{self.keypair_name}.pem"
        self.ec2_instance_id = ec2_instance_id
        self.ssh_total_wait_time = ssh_total_wait_time
        self.login_user = login_user
        self._ec2_public_ip = None
        self.local_project_path = local_project_path
    
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

        
    def handle_ssh_install_dependencies(self):
        logging.info("Handle install dependencies")
        instance = check_if_ec2_ready_for_ssh(
            instance_id=self.ec2_instance_id , 
            wait_time=self.ssh_total_wait_time, 
            delay=self.ssh_total_wait_time, 
            pem_location=self._pem_full_path_name,
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
            pem_location=self._pem_full_path_name,
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
            pem_location=self._pem_full_path_name,
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
            pem_location=self._pem_full_path_name,
            ec2_client=self._ec2_client,
            local_file=local_env,
            remote_file=remote_env,
        )


        remote_projects_folder = remote_base_path + f"/projects"
        
        logging.info("-------------------")
        logging.info(f"upload local project folder to ec2 projects")
        logging.info(f"local folder:{self.local_project_path}")
        logging.info(f"remote folder:{remote_projects_folder}")
        logging.info("-------------------")
        
        

        ssh_upload_folder_to_ec2(
            user_name=self.login_user,
            instance_id=self.ec2_instance_id,
            pem_location=self._pem_full_path_name,
            local_folder=self.local_project_path,
            remote_folder=remote_projects_folder,
            ec2_resource=self._ec2_resource,

        )