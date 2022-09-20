
from http import client
import imp
import glob
import shutil

from multiprocessing.connection import answer_challenge
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
    handle_input_project_path_question,
)

from transitions import Machine
import os
import coloredlogs, logging
from terminaltables import AsciiTable
import inquirer
from .EC2Action import EC2Action
from .EKSAction import EKSAction
from .MenuAction import MenuAction
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


class Menus(object):
    def __init__(
            self, 
            saved_config_path_base:str = None,
            ec2_config_templates :str = None,
            eks_config_templates :str = None,
            aws_access_key: str = None,
            aws_secret_access_key: str = None,
            aws_region: str = None,
            local_pem_path :str = None,
        ) -> None:
        self.saved_config_path_base = saved_config_path_base
        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region

        # template config 
        self.ec2_config_templates = ec2_config_templates
        self.eks_config_templates = eks_config_templates

        # user id 
        self._user_id = self._set_user_id()
        self._start_time = str(int(time.time()))
        # actions
        self._menus_action = None,

        # saved ec2 config file 
        self._saved_config_full_path = None,
        self._saved_ec2_config_file = None,
        self._saved_eks_config_file = None,

        # path 
        self._base_path = os.getcwd()

        # config

        self._config_yaml_dcit = {}
        self._eks_config_yaml_dcit = {}
        self._ec2_config_yaml_dcit = {}
        self._ec2_image_id = None,
        self._ec2_instance_id = None,
        self._ec2_instance_type = None,
        self._ec2_volume = None,
        self._login_user = None,
        self._ec2_tages = None,

        self._max_nodes = 100
        self._num_of_nodes = 1
        self._cleanup_resources_after_completion = None
        self._project_in_tags  = None

        self._cluster_name =f"gcd-{self._user_id}-{self._start_time}"
        self._ec2_name = f"gcd-{self._user_id}-{self._start_time}"
        self._keypair = f"gcd-{self._user_id}"
        self._local_pem_path = local_pem_path 

        # default project 
        self._template_project = self._base_path +"/config/templates/solardatatools"
        self._project_path_name = None
        self._project_absoult_path = None
        self._config_history_path = None
        

        # run-files command
        self._first_n_file = None

        # ssh command 
        self._runfiles_command = None
        self._is_ssh = False
        
        #confirmation 
        self._is_confirm_to_process = False

    def get_relative_project_folder(self):
        return self._project_path_name

    def get_cluster_file(self):
        return self._saved_eks_config_file

    def get_cleanup_after_completion(self):
        return self._cleanup_resources_after_completion

    def get_run_files_command(self):
        return self._runfiles_command
    def get_project_path(self):
        return self._project_absoult_path
        
    def get_ec2_tags(self):
        return self._ec2_tages

    def get_ec2_image_id(self):
        
        return self._ec2_image_id
    def get_ec2_instance_type(self):
        return self._ec2_instance_type

    def get_ec2_login_user(self):
        return self._login_user
        
    def get_ec2_volume(self):
        return self._ec2_volume

    def get_saved_ec2_config_file(self):
        return self._saved_ec2_config_file 
    def get_saved_eks_config_file(self):
        return self._saved_eks_config_file 

    def set_saved_eks_config_file(self, file):
        self._saved_eks_config_file  = file


    def get_ec2_export_full_path_name(self):
        return self._config_history_path + "/config-ec2.yaml"
    
    def get_eks_export_full_path_name(self):
        return self._config_history_path + "/cluster.yaml"
        
    def get_local_pem_path(self):
        return self._local_pem_path
    def get_pem_full_path_name(self):
        return self._local_pem_path +f"/{self._keypair}.pem"

    def get_keypair_name(self):
        return self._keypair

    def get_project_in_tags(self):
        return self._project_in_tags

    def get_confirmation_to_proness(self):
        return self._is_confirm_to_process

    # set user id from iam user name
    def _set_user_id(self):
        sts_client = connect_aws_client(
            client_name= "sts",
            key_id= self.aws_access_key,
            secret= self.aws_secret_access_key,
            region=self.aws_region
        )
        arn_user_name= get_iam_user_name(sts_client=sts_client)

        if arn_user_name is not None:
            return arn_user_name
        else:
            raise Exception("AWS credentials are not correct")

    def get_menus_action(self):
        return self._menus_action

    def get_is_run_custom_ssh_command(self):
        return self._is_ssh



    # set menu actions 
    def select_main_menus(self):
        logging.info("Main menus")
        menus_selection =[]
        
        inst_question = [
            inquirer.List('action',
                            message="Select action type ?",
                            choices=[
                                MenuAction.create_cloud_resources_and_start.name,
                                MenuAction.resume_from_existing.name, 
                                MenuAction.cleanup_cloud_resources.name, 
                                MenuAction.run_in_local_machine.name],
                        ),
        ]
        inst_answer = inquirer.prompt(inst_question)
        self._menus_action = inst_answer["action"]
        
        logging.info(f"Set ec2 action : {self._menus_action}")

    def select_created_cloud_config_files(self):
        logging.info("select_created_cloud_config_files")  

        config_lists = get_subfolder(parent_folder=self.saved_config_path_base)
        questions = [
            inquirer.List('dir',
                            message="Select created config path ?",
                            choices=config_lists,
                        ),
        ]
        inst_answer = inquirer.prompt(questions)
        answer =  inst_answer["dir"]
        self._saved_config_full_path = self.saved_config_path_base + f"/{answer}"
        logging.info(f"saved full path : {self._saved_config_full_path}")
        self.set_relative_saved_config_files_folder_name(name=answer)

        self._saved_ec2_config_file = self._saved_config_full_path +"/config-ec2.yaml"
        self._saved_eks_config_file = self._saved_config_full_path +"/cluster.yaml"
        print(f"self._saved_ec2_config_file {self._saved_ec2_config_file}")

        self._config_history_path = self._saved_config_full_path


    def set_relative_saved_config_files_folder_name(self,name):
        self._relative_saved_config_files_folder_name = name

    def get_relative_saved_config_files_folder_name(self):
        return self._relative_saved_config_files_folder_name

    #handle mensu action
    def handle_prepare_actions(self):
        if self._menus_action is None:
            raise Exception("No menu action selected , somehting wrong")

        if self._menus_action == MenuAction.create_cloud_resources_and_start.name:
            logging.info("crete cloud resources and start")
            logging.info("Step 1 , input project folder")
            self.handle_enter_input_project_path()
            logging.info("Step 2 , check file structur corrects")
            self.handle_verify_project_folder()
            logging.info("Step 3 , input questions")
            self.hande_proecess_files_inputs_questions()
            logging.info("Step 4 , generate cluster.yaml from tempaltes")
            self.generate_config_history_path_and_export_eks_config()
            self.import_ec2_variables_from_templates()
            self.print_variables_and_request_confirmation()



        elif self._menus_action == MenuAction.resume_from_existing.name :
            logging.info("resume from existing")
            logging.info("Step 0 , select saved config file")
            self.select_created_cloud_config_files()
            logging.info("Step 1 , input project folder")
            self.handle_enter_input_project_path()
            logging.info("Step 2 , check file structur corrects")
            self.handle_verify_project_folder()
            self.import_from_ec2_config()
            self.import_from_eks_config()
            self.print_variables_and_request_confirmation()
            


        elif self._menus_action == MenuAction.cleanup_cloud_resources.name:
            logging.info("clearnup created cloud resources")
            logging.info("Step 0 , select saved config file")
            self.select_created_cloud_config_files()
            logging.info("Step 1 , input project folder")
            self.handle_enter_input_project_path()
            logging.info("Step 2 , check file structur corrects")
            self.handle_verify_project_folder()
            self.import_from_ec2_config()
            self.import_from_eks_config()
            self.print_variables_and_request_confirmation()
            

        elif self._menus_action == MenuAction.run_in_local_machine:
            logging.info("run in local machine")
            self.handle_enter_input_project_path()
            logging.info("Step 3 , check file structur corrects")
            self.handle_verify_project_folder()



    def print_variables_and_request_confirmation(self):

        # if self._menus_action == MenuAction.create_cloud_resources_and_start.name:

        cloud_resource = [
            ["Parameters","Details"],
            ['project full path', self._project_absoult_path],
            ['project folder', self._project_path_name],
            ['number of process files', self._first_n_file],
            ['number of  generated instances', self._num_of_nodes],
            ['max nodes size',self._max_nodes],
            ["cleanup cloud resources after completion",self._cleanup_resources_after_completion],
            ["Generate EC2 bastion name",self._ec2_name],
            ["SSH command", self._runfiles_command],
            ["Generate EKS cluster name",self._cluster_name],
            ['poject in tags',self._project_in_tags],
        ]
        table1 = AsciiTable(cloud_resource)
        print(table1.table)
        ec2_resources = [
            ["Parameters","Details"],
            ['ec2_tags', self._ec2_tages],
            ['ec2 image id', self._ec2_image_id],
            ['ec2 instances type', self._ec2_instance_type],
            ['ec2 volume', self._ec2_volume],
            ['ec2 keypair', self._keypair],
            ['pem location', self._local_pem_path],

        ]
        table2 = AsciiTable(ec2_resources)
        print(table2.table)

        self._is_confirm_to_process = handle_yes_or_no_question(
            input_question="Comfim to process (must be yes/no)",
            default_answer="yes"
        )
        if self._is_confirm_to_process and self._menus_action == MenuAction.create_cloud_resources_and_start.name:
            self._config_history_path = self.saved_config_path_base +f"/{self._ec2_name}"
            if not os.path.exists(self._config_history_path):
                os.makedirs(self._config_history_path)
            
            self.set_relative_saved_config_files_folder_name(name=self._ec2_name)
          
            export_file = self._config_history_path +"/cluster.yaml"
            self.set_saved_eks_config_file(file=export_file)

            write_aws_setting_to_yaml(
                file=export_file, 
                setting=self._eks_config_yaml_dcit
            )
            logging.info("Export eks config")

    def import_from_ec2_config(self):
        logging.info(f"import from ec2 {self._saved_ec2_config_file}")
        if self._saved_ec2_config_file is None:
            raise Exception(f"saved_ec2_config_file is None") 
        if not exists(self._saved_ec2_config_file):
            raise Exception("saved_ec2_config_file does not exist")
        self._ec2_config_yaml_dcit = convert_yaml_to_json(yaml_file=self._saved_ec2_config_file)
  
        verify_keys_in_ec2_configfile(config_dict=self._ec2_config_yaml_dcit)
    


    def import_from_eks_config(self):
        logging.info("import from eks")
        if self._saved_eks_config_file is None:
            raise Exception(f"saved_eks_config_file is None") 
        if not exists(self._saved_eks_config_file):
            raise Exception("saved_eks_config_file does not exist")
        self._eks_config_yaml_dcit = convert_yaml_to_json(yaml_file=self._saved_eks_config_file)
        verify_keys_in_eks_configfile(config_dict=self._eks_config_yaml_dcit)



    def hande_proecess_files_inputs_questions(self):

        self._is_ssh  = handle_yes_or_no_question(
            input_question=f"Run any ssh command? If `no`, there will be instructions show how to use run-files command",
            default_answer="no"
        )
        logging.info("Project name")
        self._project_in_tags = hanlde_input_project_name_in_tag(
            input_question="Enter the name of project. This will be listed in all created cloud resources, and it's used for managing budege. (It's not the same as project path)",
            default_answer = self._project_in_tags
    
        )
        if self._is_ssh is False:
            is_process_default_file  = handle_yes_or_no_question(
                input_question=f"Do you want to process the defined files in config.yaml?",
                default_answer="no"
            )

            if is_process_default_file is False:
                self._process_first_n_files = handle_input_number_of_process_files_question(
                    input_question="How many files you would like process? \n Input an postive integer number. \n Input '0' to process all files in the data bucket \n Otherwise, It processes first 'n'( n as input) number files.",
                    default_answer=1,
                )
                logging.info(f"Process first {self._process_first_n_files} files")
            else:
                self._process_first_n_files = None
                logging.info("Process default files")

            logging.info("Input the number of instances ")
            self._num_of_nodes = handle_input_number_of_scale_instances_question(
                input_question="How many instances you would like to generate to run this application in parallel? \n Input an postive integer: ",
                default_answer=1,
                max_node= self._max_nodes
            )
            logging.info(f"Number of generated instances:{self._num_of_nodes}")

            self._cleanup_resources_after_completion = handle_yes_or_no_question(
                input_question="Do you want to clean up cloud resources after completion?",
                default_answer="yes"
            )
            if is_process_default_file is True:
                self._runfiles_command = f"python3 main.py run-files -s {self._num_of_nodes} -p {self._project_path_name}"
            else: 
                self._runfiles_command = f"python3 main.py run-files -n {self._process_first_n_files} -s {self._num_of_nodes} -p {self._project_path_name}"


    def handle_enter_input_project_path(self):
        default_project = self._template_project
        input_project_path = handle_input_project_path_question(
            input_question="Enter project folder (Hit `Enter` button to use default path",
            default_answer=default_project
        )
        self._project_path_name = basename(input_project_path)
        self._project_absoult_path = self._base_path + f"/projects/{self._project_path_name}"

        logging.info(f"Copy {input_project_path} to {self._project_absoult_path}")

        if not os.path.exists(self._project_absoult_path):
            logging.info(f"Create {self._project_absoult_path}")
            os.makedirs(self._project_absoult_path)
        shutil.copytree(input_project_path, self._project_absoult_path, dirs_exist_ok=True)  # 3.8+ only!



    def handle_verify_project_folder(self):
        files_check_list = ["entrypoint.py","Dockerfile","requirements.txt","config.yaml"]
        for file in files_check_list:
            full_path_file = self._project_absoult_path + "/"+file
            if not exists(full_path_file):
                raise Exception(f"{full_path_file} does not exist!!")
            logging.info(f"{file} exists")
        logging.info("Verify files list success")
        config_yaml = self._project_absoult_path + "/config.yaml"
        try:
            self._config_yaml_dcit= convert_yaml_to_json(yaml_file=config_yaml)
        except Exception as e:
            raise Exception(f"convert config yaml failed")

        verify_keys_in_configfile(
            config_dict=self._config_yaml_dcit
        )
        
    def generate_config_history_path_and_export_eks_config(self):
        logging.info("import from tempaltes and change eks variables")
        # import from templates
        self._eks_config_yaml_dcit = convert_yaml_to_json(
            yaml_file=self.eks_config_templates
        )
        print(f"self._user_id {self._user_id}")
        # change variables 
        # modify cluster name 
        self._eks_config_yaml_dcit['metadata']['name'] = self._cluster_name
        self._eks_config_yaml_dcit['metadata']['region'] = self.aws_region
        self._eks_config_yaml_dcit['metadata']['tags']['project'] = self._project_in_tags
        self._eks_config_yaml_dcit['nodeGroups'][0]['tags']['project'] = self._project_in_tags
        # generate history folder
        
    def import_ec2_variables_from_templates(self):
        ec2_config = convert_yaml_to_json(
            yaml_file=self.ec2_config_templates
        )
        
        verify_keys_in_ec2_configfile(config_dict=ec2_config)

        self._ec2_image_id = ec2_config['ec2_image_id']
        self._ec2_instance_type = ec2_config['ec2_instance_type']
        self._ec2_volume = ec2_config['ec2_volume']
        self._login_user = ec2_config['login_user']
        self._ec2_tages = ec2_config['tags']
        self._ec2_tages.append({"Key":"Name", "Value":self._ec2_name})
        self._ec2_tages.append({"Key":"project", "Value":self._project_in_tags})


    def delete_saved_config_folder(self):
        logging.info("Delete saved config folder")
        if not os.path.exists(self._config_history_path):
            raise Exception(f"{self._config_history_path} does not exist")
        try:
            shutil.rmtree(self._config_history_path)
        except Exception as e:
            raise Exception(f"Dlete {self._config_history_path} failded")

    def delete_project_folder(self):
        logging.info("Delete project folder")
        if not os.path.exists(self._project_absoult_path):
            raise Exception(f"{self._project_absoult_path} does not exist")
        try:
            shutil.rmtree(self._project_absoult_path)
        except Exception as e:
            raise Exception(f"Dlete {self._project_absoult_path} failded")


        
def get_subfolder(parent_folder) -> list:
    if not os.path.exists(parent_folder):
        raise Exception (f"{parent_folder} does not exist")
    config_lists= []
    for fullpath, j , y in  os.walk(parent_folder):
        relative_path = remove_partent_path_from_absolute_path(parent_path=parent_folder, absolut_path=fullpath)
        if relative_path == ".":
            continue
        config_lists.append(relative_path)
    return config_lists


def remove_partent_path_from_absolute_path(parent_path, absolut_path) -> str:
    relative_path = os.path.relpath(absolut_path, parent_path)
    return relative_path


def verify_keys_in_configfile(config_dict:dict):
    try:
        assert 'worker_config' in config_dict
        # assert 'services_config_list' in self._config
        # assert 'aws_config' in self._config


        # worker_config
        worker_config_dict = config_dict['worker_config']
        assert 'data_bucket' in worker_config_dict
        assert 'default_process_files'in  worker_config_dict
        assert 'data_file_type' in worker_config_dict
        assert 'process_column_keywords' in worker_config_dict
        assert 'saved_bucket' in worker_config_dict

        logging.info("Verify config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert error {e}")



def verify_keys_in_ec2_configfile(config_dict:dict):

    try:
   
        assert 'ec2_image_id' in config_dict
        assert 'ec2_instance_id' in config_dict
        assert 'ec2_volume' in config_dict
        assert 'key_pair_name' in config_dict
        assert 'login_user' in config_dict
        assert 'tags' in config_dict
        assert 'SecurityGroupIds' in config_dict
        assert 'vpc_id' in config_dict

        logging.info("Verify ec2 config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert ec2 error {e}")


def verify_keys_in_eks_configfile(config_dict:dict):
    try:
        assert 'apiVersion' in config_dict
        assert 'metadata' in config_dict
        assert 'nodeGroups' in config_dict
        # assert 'services_config_list' in self._config
        # assert 'aws_config' in self._config


        # worker_config
        metadata = config_dict['metadata']
        assert 'name' in metadata
        assert 'region'in  metadata
        assert 'tags' in metadata
        # assert metadata['tags']['project'] != '<auto-generated>'

        nodeGroups = config_dict['nodeGroups']
        assert len(nodeGroups) > 0
        # assert nodeGroups[0]['tags']['project'] != '<auto-generated>'

        logging.info("Verify eks config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert eks error {e}")

