
from glob import escape
import readline
from os.path import relpath
from os.path import normpath, basename
from pathlib import Path
from os.path import exists
import time

import re
import socket
from unittest import result


from transitions import Machine
import os
import coloredlogs, logging
from terminaltables import AsciiTable
import inquirer

from mainmenu.classes.constants.EC2Actions import EC2Actions
from .utilities.verification import verify_keys_in_ec2_configfile, verify_keys_in_eks_configfile
from .utilities.handle_inputs import (
    select_is_breaking_ssh,
    handle_yes_or_no_question
)
from .constants.InputDescriptions import InputDescriptions
from .utilities.convert_yaml import convert_yaml_to_json,write_aws_setting_to_yaml
from .utilities.aws_utitlties import (
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
    delete_key_pair,
    create_security_group,
    create_key_pair,
    create_instance,
    export_ec2_parameters_to_yaml,
    run_command_in_ec2_ssh,
    check_if_ec2_ready_for_ssh,
    get_public_ip,
    ssh_upload_folder_to_ec2,
    upload_file_to_sc2,
    ssh_download_folder_from_ec2
)

from .constants.AWSActions import AWSActions
from .constants.EC2Status import EC2Status
from .constants.EKSActions import EKSActions

class AWSServices(object):

    def __init__(
            self, 
            keypair_name:str = None,
            local_pem_path:str = None,
            aws_access_key: str = None,
            aws_secret_access_key: str = None,
            aws_region: str = None,
            saved_config_path_base :str = None,
            ec2_tags :list = None,
            local_temp_project_path = None,
            project_name :str = None,
            origin_project_path:str = None,

        ) -> None:

        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region

        self._ssh_total_wait_time = 90
        self._ssh_wait_time_interval = 1

        self._import_ec2_config_file = None
        self._export_ec2_config_file = None

        self._created_eks_config_file = None


        self._aws_action= None
        self.local_pem_path = local_pem_path
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
        self._history_id = None
        # EC2 variables
        self._tags = ec2_tags
        self._login_user = None
        self._ec2_image_id = None
        self._ec2_instance_type = None
        self._ec2_volume = None
        self._ec2_instance_id = None
        self.securitygroup_name = None
        self._securitygroup_ids = []
        self.key_pair_name = keypair_name
        self._default_vpc_id = None

        self.saved_config_path_base = saved_config_path_base
        self._config_history_path= None
        self.local_temp_project_path = local_temp_project_path
        self.project_name = project_name
        self._origin_project_path = origin_project_path

        # eks variables
        self._cluster_name = None
        self._nodegroup_name = None
        
    def get_origin_project_path(self):
        return  self._origin_project_path


    def get_ec2_name_from_tags(self):
        print(f"self._tags :{self._tags}")
        for tag in self._tags:
            if "Key" not in tag:
                continue
            if "Value" not in tag:
                continue
            if tag['Key'] == "Name":
                ec2_name = tag['Value']
                return ec2_name
        logging.error("Noe ec2 name in tags")
        return None

    def get_project_from_tags(self):
        for tag in self._tags:
            if "Key" not in tag:
                continue
            if "Value" not in tag:
                continue
            if tag['Key'] == "project":
                project_tag = tag['Value']
                return project_tag
        logging.error("Noe project in tags")
        return None

    def get_config_history_path(self):
        return self._config_history_path

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

    

    def handle_aws_actions(self, action):
        # if self._aws_action == AWSActions.get_default_vpc_id.name():
        #     logging.info("Get default VPC id")
        if action == AWSActions.create_securitygroup.name:
            logging.info("Create security group action")
            if self._default_vpc_id is None:
                raise Exception("default vpc id is None")
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
                self._securitygroup_ids = [sg_id]
                logging.info(f"Found security groupd with name: {self.securitygroup_name}  ids: {self._securitygroup_ids}")
                self._securitygroup_ids = [sg_id]
        elif action == AWSActions.delete_securitygroup.name:
            logging.info("Delete security group action")
            sg_id = get_security_group_id_with_name(
                ec2_client=self._ec2_client, 
                group_name=self.securitygroup_name)
            if sg_id is None:
                logging.info(f"No security group name :{self.securitygroup_name} found")
            else:
                logging.info(f"Found security groupd with name: {self.securitygroup_name}  id: {sg_id}")
                self._securitygroup_ids = [sg_id]
                logging.info(f"Deleting {self._securitygroup_ids}")
                delete_security_group(ec2_client=self._ec2_client, group_id=sg_id)

        elif action == AWSActions.create_keypair.name:
            logging.info("Create keypair action")
            if self.key_pair_name is None:
                raise ValueError("Key pair name is None")
            if not check_keypair_exist(
                ec2_client=self._ec2_client, 
                keypair_anme=self.key_pair_name
                ):
                
                logging.info(f"keypair:{self.key_pair_name} does not exist create a new keypair in {self.local_pem_path}")
                create_key_pair(ec2_client=self._ec2_client, keyname=self.key_pair_name, file_location=self.local_pem_path)
            else:
                logging.info(f"keypair:{self.key_pair_name} exist")

        elif action == AWSActions.delete_keypair.name:
            logging.info("Delete keypair action")
            if not check_keypair_exist(ec2_client=self._ec2_client, keypair_anme=self.key_pair_name):
                logging.info(f"keypair:{self.key_pair_name} does not exist do nothing ")
            else:
                logging.info(f"Deleting:{self.key_pair_name} ")
                delete_key_pair(ec2_client=self._ec2_client, key_name=self.key_pair_name)
                local_pem  = self.get_pem_file_full_path_name()
                if exists(local_pem):
                    os.remove(local_pem)
                    logging.info(f"Delete local pem: {local_pem} success")
        elif action == AWSActions.get_default_vpc_id.name:
            self.get_default_vpc_id()
            logging.info(f"get and set default vpc id :{self._default_vpc_id} ")

        elif action == AWSActions.create_ec2_instance.name:
            logging.info("Create ec2 action")
            try:
                if self._securitygroup_ids is None or not len(self._securitygroup_ids):
                    raise Exception("securitygroup_ids is None")
                if self.key_pair_name is None:
                    raise Exception("key_pair_name is None")

                ec2_instance_id = create_instance(     
                    ImageId=self._ec2_image_id,
                    InstanceType = self._ec2_instance_type,
                    key_piar_name = self.key_pair_name,
                    ec2_client=self._ec2_client,
                    tags= self._tags,
                    SecurityGroupIds = self._securitygroup_ids,
                    volume=self._ec2_volume
                )
                logging.info(f"ec2_instance_id: {ec2_instance_id}")
                self._ec2_instance_id = ec2_instance_id
                logging.info("-------------------")
                logging.info(f"Create ec2 bastion completed")
                logging.info("-------------------")
            except Exception as e:
                raise Exception(f"Create ec2 instance failed: \n {e}")

            

    def get_ec2_status(self):
        if self._ec2_instance_id is None:
            raise Exception("EC2 id does not exist")
        self._ec2_status = get_ec2_state_from_id(
            ec2_client=self._ec2_client,
            id=self._ec2_instance_id
        )

        return self._ec2_status



    def wake_up_ec2(self, wait_time:int = 90, delay:int = 1):
        # import from ec2 file
        logging.info("Wake up ec2")
        if self._ec2_instance_id is None:
            raise Exception("ec2 instance id is None, Import from exsiting file or create a new one")
        is_ec2_state_ready = False
        while wait_time > 0 or not is_ec2_state_ready:
                wait_time -= delay
                ec2_state =  self.get_ec2_status()
                logging.info(f"ec2_state :{ec2_state} waitng:{wait_time}")
                if ec2_state == EC2Status.stopped.name or ec2_state == EC2Status.running.name:
                    logging.info(f"In stopped or running running sate")
                    is_ec2_state_ready = True
                    break
                wait_time.sleep(delay)

        if is_ec2_state_ready is False:
            raise ValueError(f"Wait ec2 state overtime :{ec2_state}")

        if ec2_state == EC2Status.stopped.name:
            logging.info("EC2 in stop state, wake up ec2")
            # self.set_ec2_action(action=EC2Action.start.name)
            self.handle_ec2_action(action=EC2Actions.start.name)
        
        if ec2_state == EC2Status.running.name:
            logging.info("EC2 in running state")
            pass

        return 

    def import_from_existing_ec2_config(self, config_file):
        logging.info(f"import from ec2 {config_file}")
        if config_file is None:
            raise Exception(f"saved_ec2_config_file is None") 
        if not exists(config_file):
            raise Exception("saved_ec2_config_file does not exist")
        self._import_ec2_config_file = config_file
        ec2_config_dict = convert_yaml_to_json(yaml_file=config_file)
        verify_keys_in_ec2_configfile(config_dict=ec2_config_dict)
        self.key_pair_name = ec2_config_dict['key_pair_name']
        self._tags = ec2_config_dict['tags']
        self._ec2_image_id = ec2_config_dict['ec2_image_id']
        self._ec2_instance_type = ec2_config_dict['ec2_instance_type']
        self._ec2_volume = ec2_config_dict['ec2_volume']
        self._login_user = ec2_config_dict['login_user']
        self._ec2_instance_id = ec2_config_dict['ec2_instance_id']
        self.securitygroup_name = ec2_config_dict['securitygroup_name']

        if self._ec2_instance_id is None or self._ec2_instance_id == "":
            raise ValueError("ec2 instance id in config file is None, Import wrong file or file is corrupted")

        return 

    def create_ec2_from_template_file(self, import_file:str,):
        logging.info(f"create ec2 from {import_file}")
        if import_file is None:
            raise Exception(f"ec2 config file is None") 
        if not exists(import_file):
            raise Exception("ec2 config file does not exist")
        self._import_ec2_config_file = import_file
        ec2_config_dict = convert_yaml_to_json(yaml_file=import_file)
        verify_keys_in_ec2_configfile(config_dict=ec2_config_dict)
        self._ec2_image_id = ec2_config_dict['ec2_image_id']
        self._ec2_instance_type = ec2_config_dict['ec2_instance_type']
        self._ec2_volume = ec2_config_dict['ec2_volume']
        self._login_user = ec2_config_dict['login_user']
        self.securitygroup_name = ec2_config_dict['securitygroup_name']

        ec2_name = self.get_ec2_name_from_tags()
        if ec2_name is None:
            raise Exception("No ec2 name in tags")
        # step 1 , check keypair
        self.handle_aws_actions(action=AWSActions.create_keypair.name)
        # step 2 . get default vpc id to create security group
        self.handle_aws_actions(action=AWSActions.get_default_vpc_id.name)
        # step 3 . chcek security group
        self.handle_aws_actions(action=AWSActions.create_securitygroup.name)
        securitygroup_ids = self.get_security_group_ids()
        # step 4 . create instance
        self.handle_aws_actions(action=AWSActions.create_ec2_instance.name)

        # step 4 , generate history path and export ec2 setting
        self.generate_config_history_path(id=ec2_name)
        export_ec2_file = self._config_history_path + "/config-ec2.yaml"
        self.export_ec2_params_to_file(
            export_file=export_ec2_file
        )
        # step 5 , install dependencies
        self.hanle_ec2_setup_dependencies()
        logging.info("Inatallization completed")


    
    def hanle_ec2_setup_dependencies(self):
        logging.info("Start setup gcd environments on AWS ec2")

        instance = check_if_ec2_ready_for_ssh(
            instance_id=self._ec2_instance_id , 
            wait_time=self._ssh_total_wait_time, 
            delay=self._ssh_wait_time_interval, 
            pem_location=self.get_pem_file_full_path_name(),
            user_name=self._login_user)

        logging.info(f"instance ready :{instance}")

        self._ec2_public_ip = get_public_ip(
            ec2_client=self._ec2_client,
            instance_id=self._ec2_instance_id
        )
        logging.info("---------------------")
        logging.info(f"public_ip :{self._ec2_public_ip}")
        logging.info("---------------------")
        # upload install.sh
        logging.info("-------------------")
        logging.info(f"upload install.sh")
        logging.info("-------------------")
        # upload .env
        local_env = "./deploy/install.sh"
        remote_env=f"/home/{self._login_user}/install.sh"
        upload_file_to_sc2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self._ec2_client,
            local_file=local_env,
            remote_file=remote_env,
        )
        # run install.sh
        logging.info("=============================")
        logging.info("Run install.sh ")
        logging.info("=============================")
        command = f"bash /home/{self._login_user}/install.sh"
        run_command_in_ec2_ssh(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            command=command,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self._ec2_client
        )

        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy"
        # upload .env
        logging.info("-------------------")
        logging.info(f"upload .env")
        logging.info("-------------------")
        # upload .env
        local_env = ".env"
        
        remote_env=f"{remote_base_path}/.env"
        upload_file_to_sc2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
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
            user_name= self._login_user,
            instance_id= self._ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self._ec2_client,
            command=ssh_command
        )
    
        remote_projects_folder =f"{remote_base_path}/{self.project_name}"
        
        logging.info("-------------------")
        logging.info(f"upload local project folder to ec2 projects")
        logging.info(f"local folder:{self.local_temp_project_path}")
        logging.info(f"remote folder:{remote_projects_folder}")
        logging.info("-------------------")
        
        

        ssh_upload_folder_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            local_project_path_base=self.local_temp_project_path,
            remote_project_path_base=remote_projects_folder,
            ec2_resource=self._ec2_resource,

        )


    def export_ec2_params_to_file(self, export_file):
        self._export_ec2_config_file = export_file
        # check path exist
        path, file = os.path.split(export_file)
        if not os.path.exists(path):
            os.mkdir(path)

        config_dict  = {}
        config_dict['securitygroup_name'] = self.securitygroup_name
        config_dict['ec2_image_id'] = self._ec2_image_id
        config_dict['ec2_instance_id'] = self._ec2_instance_id
        config_dict['ec2_instance_type'] = self._ec2_instance_type
        config_dict['ec2_volume'] = self._ec2_volume
        config_dict['key_pair_name'] = self.key_pair_name
        config_dict['login_user'] = self._login_user
        config_dict['tags'] = self._tags
        
        write_aws_setting_to_yaml(
                file=export_file, 
                setting=config_dict
            )

        logging.info("Export eks config")
        return 
        
    def run_ssh_debug_mode(self):
        # Run any command 
        logging.info("enter debug mode")
        is_breaking = False
        while not is_breaking:
            custom_ssh_command = self.handle_input_ssh_custom_command()
            self.run_ssh_command(
                ssh_command=custom_ssh_command
            )
            logging.info("SSH command completed")
            is_breaking = self.input_is_breaking_ssh()
        logging.info("exit debug mode")
    
    def handle_input_ssh_custom_command(self):
        custom_command = input(f"Please type your command: ")
        return custom_command

    def run_ssh_command(self, ssh_command:str, ):
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/"
        full_ssh_command = f"cd {remote_base_path} \n source ./venv/bin/activate \n {ssh_command} "
        pem_file_full_path_name = self.get_pem_file_full_path_name()
        run_command_in_ec2_ssh(
            user_name= self._login_user,
            instance_id= self._ec2_instance_id,
            pem_location=pem_file_full_path_name,
            ec2_client=self._ec2_client,
            command=full_ssh_command
        )

    def input_is_breaking_ssh(self):
        is_breaking = select_is_breaking_ssh()
        return is_breaking

    def handle_ec2_action(self , action:str):
        if action is None:
            raise ValueError("action is None")

        if action == EC2Actions.create.name:
            logging.info("Create new EC2 instances")
            try:
                if self._securitygroup_ids is None:
                    raise Exception("securitygroup_ids is None")
                if self.key_pair_name is None:
                    raise Exception("key_pair_name is None")

                ec2_instance_id = create_instance(     
                    ImageId=self._ec2_image_id,
                    InstanceType = self._ec2_instance_type,
                    key_piar_name = self.key_pair_name,
                    ec2_client=self._ec2_client,
                    tags= self._tags,
                    SecurityGroupIds = self._securitygroup_ids,
                    volume=self._ec2_volume
                )
                logging.info(f"ec2_instance_id: {ec2_instance_id}")
                self._ec2_instance_id = ec2_instance_id
                logging.info("-------------------")
                logging.info(f"Create ec2 bastion completed")
                logging.info("-------------------")

            except Exception as e:
                raise Exception(f"Create ec2 instance failed {e}")
        elif action == EC2Actions.start.name:
            if self._ec2_instance_id is not None:
                res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).start() #for stopping an ec2 instance
                instance = check_if_ec2_ready_for_ssh(instance_id=self._ec2_instance_id, wait_time=self._ssh_total_wait_time, delay=self._ssh_wait_time_interval, pem_location=self.get_pem_file_full_path_name(),user_name=self._login_user)
                self._ec2_public_ip = get_public_ip(
                    ec2_client=self._ec2_client,
                    instance_id=self._ec2_instance_id
                )
                logging.info("---------------------------------")
                logging.info(f"public_ip :{self._ec2_public_ip}")
                logging.info("---------------------------------")
                logging.info("Ec2 start")
                
        elif action == EC2Actions.stop.name:
            if self._ec2_instance_id is not None:
                res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).stop() #for stopping an ec2 instance
            else:
                logging.error("ec2_resource id is empty")
            return
        elif action == EC2Actions.terminate.name:
            logging.info("Get ec2 terminate")
            if self._ec2_instance_id is not None:
                res_term  = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).terminate() #for terminate an ec2 insta
            else:
                logging.error("ec2_resource id is empty")
            return

    def ssh_upload_folder(self, local_project_path, project_name):

        remote_projects_path = f"/home/{self._login_user}/gismo-cloud-deploy/{project_name}"

        is_update_folder = handle_yes_or_no_question(
            input_question=InputDescriptions.is_upload_folder_question.value,
            default_answer="yes"
        )
        print("--------------------------------------")
        print(f"is_update_folder :{is_update_folder}")
        print(f"local_project_path {local_project_path} \n remote_projects_path {remote_projects_path}")
        if is_update_folder is False:
            return 

        ssh_upload_folder_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            local_project_path_base=local_project_path,
            remote_project_path_base=remote_projects_path,
            ec2_resource=self._ec2_resource,

        )
        return 

    def ssh_download_results_to_originl_project_path(self ):
        if self._origin_project_path is None:
            raise ValueError(f"origin_project_path is None")
        if not exists(self._origin_project_path):
            raise Exception(f"{self._origin_project_path} does not exist")
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy"
        remote_projects_results_folder =f"{remote_base_path}/{self.project_name}/results"
        self._origin_project_results_path = self._origin_project_path +"/results"
        if not os.path.exists(self._origin_project_results_path):
            logging.warning(f"{self._origin_project_results_path} does not exist")
            os.mkdir(self._origin_project_results_path)
            logging.info(f"{self._origin_project_results_path} create success")

        logging.info(f"download results from {remote_projects_results_folder} to {self._origin_project_results_path}")
        ssh_download_folder_from_ec2(
            ec2_resource=self._ec2_resource,
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            remote_folder=remote_projects_results_folder,
            local_folder=self._origin_project_results_path,
        )

    def handle_ssh_eks_action(
        self,
        eks_action:str , 
        cluster_name:str,
        nodegroup_name:str,
        ):

        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy"
        ec2_name = self.get_ec2_name_from_tags()
        remote_cluster_file =f"{remote_base_path}/created_resources_history/{ec2_name}/cluster.yaml"

        self._cluster_name = cluster_name
        self._nodegroup_name = nodegroup_name
        ssh_command_list = {}

        if cluster_name is None or nodegroup_name is None:
            raise Exception(f"cluster_name {cluster_name} or f{nodegroup_name} is None")

        if eks_action == EKSActions.create.name:
            
            logging.info("SSH create eks")
            command = f"eksctl create cluster -f {remote_cluster_file}"
            ssh_command_list['Create EKS cluster'] = command

        elif eks_action == EKSActions.delete.name:
            logging.info("set delete eks culster command ")
            # scale down if cluster exist
            scaledown_command =  f"rec=\"$(eksctl get cluster | grep {cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl scale nodegroup --cluster {cluster_name} --name {nodegroup_name} --nodes 0; fi"
            ssh_command_list['scaledonw cluster'] = scaledown_command
            # delete cluster if cluster exist
            delete_eks_command =  f"rec=\"$(eksctl get cluster | grep {cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl delete cluster -f {remote_cluster_file}; fi"

            ssh_command_list['Delete EKS cluster'] = delete_eks_command

        elif eks_action == EKSActions.list.name:
            logging.info("Run list eks")
            command = f"eksctl get cluster"
            ssh_command_list['List EKS cluster'] = command

        elif eks_action == EKSActions.scaledownzero.name:
            logging.info("SSH scale down zero eks")
            command = f"rec=\"$(eksctl get cluster | grep {cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl scale nodegroup --cluster {cluster_name} --name {nodegroup_name} --nodes 0; fi"
            ssh_command_list['Scale down eks'] = command

        for description, command in ssh_command_list.items():
            logging.info(description)
            logging.info(command)
            try:
                run_command_in_ec2_ssh(
                    user_name=self._login_user,
                    instance_id=self._ec2_instance_id,
                    command=command,
                    pem_location=self.get_pem_file_full_path_name(),
                    ec2_client=self._ec2_client
                )
            except Exception as e:
                raise Exception(f"run eks command {description} file failed \n {e}")
    

    def generate_eks_config_and_export(self, import_file:str):
        logging.info("import from tempaltes and change eks variables")
        eks_config_yaml_dcit = convert_yaml_to_json(
            yaml_file=import_file
        )
        ec2_name = self.get_ec2_name_from_tags()
        if ec2_name is None:
            raise Exception("No ec2 name in tags")

        project_tag = self.get_project_from_tags()
        if project_tag is None:
            project_tag = ec2_name


        self._cluster_name = ec2_name
        self._nodegroup_name = eks_config_yaml_dcit['nodeGroups'][0]['name']

        eks_config_yaml_dcit['metadata']['name'] = self._cluster_name
        eks_config_yaml_dcit['metadata']['region'] = self.aws_region
        eks_config_yaml_dcit['metadata']['tags']['project'] = project_tag
        eks_config_yaml_dcit['nodeGroups'][0]['tags']['project'] = project_tag

        # export file 
        self._created_eks_config_file = self._config_history_path +"/cluster.yaml"
        verify_keys_in_eks_configfile(config_dict=eks_config_yaml_dcit)
        write_aws_setting_to_yaml(
            file=self._created_eks_config_file, 
            setting=eks_config_yaml_dcit
        )
    
        logging.info("Export eks config success")
        return 
        

    def generate_config_history_path(self, id):
        self._config_history_path = self.saved_config_path_base +f"/{id}"
        if not os.path.exists(self._config_history_path):
            os.makedirs(self._config_history_path)
            logging.info(f"Create {self._config_history_path} success")

    def ssh_update_eks_cluster_file(self):
        ec2_name = self.get_ec2_name_from_tags()
        remote_cluster = f"/home/{self._login_user}/gismo-cloud-deploy/created_resources_history/{ec2_name}/cluster.yaml"
        
        upload_file_to_sc2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self.get_pem_file_full_path_name(),
            ec2_client=self._ec2_client,
            local_file=self._created_eks_config_file,
            remote_file=remote_cluster,
        )