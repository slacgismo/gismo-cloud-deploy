
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
    check_keypair_name_exists,
    delete_security_group,
    delete_key_pair
    
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

class HandleAWS(object):

    def __init__(
            self, 
            keypair_name:str = None,
            securitygroup_name = None,
            local_pem_path:str = None,
            aws_access_key: str = None,
            aws_secret_access_key: str = None,
            aws_region: str = None,
            tags:list = []

        ) -> None:

        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.securitygroup_name = securitygroup_name
        self._securitygroup_ids = []
        self.key_pair_name = keypair_name
        self._default_vpc_id = None
        self._tags = tags
        self._aws_action= None
        self.local_pem_path = local_pem_path
        self._ec2_client  = connect_aws_client(
            client_name='ec2',
            key_id= self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )

    def set_aws_action(self, action):
        self._aws_action = action
    
    def get_aws_action(self):
        return self._aws_action

    def get_security_group_ids(self):
        return self._securitygroup_ids

    def get_default_vpc_id(self):
        
        self._default_vpc_id = get_default_vpc_id(
            ec2_client=self._ec2_client 
        )
        return self._default_vpc_id

    def get_keypair_name(self):
        return self.key_pair_name

    def get_pem_file_full_path_name(self):
        full_path = self.local_pem_path +f"/{self.key_pair_name}.pem"
        return full_path
    
    
    def get_aws_action(self):
        return self._aws_action



    def handle_aws_actions(self):
        # if self._aws_action == AWSActions.get_default_vpc_id.name():
        #     logging.info("Get default VPC id")
        if self._aws_action == AWSActions.create_securitygroup.name:
            logging.info("Create security group")
            if self._default_vpc_id is None:
                raise Exception("Vpc id is None")
            sg_id = get_security_group_id_with_name(ec2_client=self._ec2_client, group_name=self.securitygroup_name)
            if sg_id is None:
                security_info_dict = create_security_group(
                        ec2_client=self._ec2_client,
                        vpc_id=self._default_vpc_id,
                        tags=self._tags,
                        group_name=self.securitygroup_name
                    )
                self._securitygroup_ids = [security_info_dict['security_group_id']]
                logging.info(f"Create SecurityGroupIds : {self._securitygroup_ids} in vpc_id:{self._default_vpc_id} success")
            else:
                logging.info(f"Found security groupd with name: {self.securitygroup_name}  id: {sg_id}")
                self._securitygroup_ids = [sg_id]
        elif self._aws_action == AWSActions.delete_securitygroup.name:
            logging.info("Delete security group")
            sg_id = get_security_group_id_with_name(ec2_client=self._ec2_client, group_name=self.securitygroup_name)
            if sg_id is None:
                logging.info(f"No security group name :{self.securitygroup_name} found")
            else:
                logging.info(f"Found security groupd with name: {self.securitygroup_name}  id: {sg_id}")
                self._securitygroup_ids = [sg_id]
                logging.info(f"Deleting {self._securitygroup_ids}")
                delete_security_group(ec2_client=self._ec2_client, group_id=sg_id)

        elif self._aws_action == AWSActions.create_keypair.name:
            logging.info("Create keypair")
            if not check_keypair_exist(ec2_client=self._ec2_client, keypair_anme=self.key_pair_name):
                logging.info(f"keypair:{self.key_pair_name} does not exist create a new keypair in {self.local_pem_path}")
                create_key_pair(ec2_client=self._ec2_client, keyname=self.key_pair_name, file_location=self.local_pem_path)
            else:
                logging.info(f"keypair:{self.key_pair_name} exist")

        elif self._aws_action == AWSActions.delete_keypair.name:
            logging.info("Delete keypair")
            if not check_keypair_exist(ec2_client=self._ec2_client, keypair_anme=self.key_pair_name):
                logging.info(f"keypair:{self.key_pair_name} does not exist do nothing ")
            else:
                logging.info(f"Deleting:{self.key_pair_name} ")
                delete_key_pair(ec2_client=self._ec2_client, key_name=self.key_pair_name)
                local_pem  = self.get_pem_file_full_path_name()
                if exists(local_pem):
                    os.remove(local_pem)
                    logging.info(f"Delete local pem: {local_pem} success")