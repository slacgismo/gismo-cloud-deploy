
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

class HandleEC2Bastion(object):
    states=[
        'system_stop',  
        'system_initial',
        'cloud_resources_ready',
        'ec2_ready',
        'eks_ready',
        'cleanup',
        ]

    def __init__(
            self, 
            aws_access_key: str = None,
            aws_secret_access_key: str = None,
            aws_region: str = None,
        ) -> None:
        self._ec2_config_file = 'ec2/config-ec2.yaml'
        self._gcd_config_file = 'config.yaml'
        self._eks_configfile = 'eks/cluster.yaml'


        self.aws_access_key =aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self._project_full_path = None


        self._use_deafualt_vpc = 'yes'
        self._is_creating_sg ='yes'
        self._is_creating_keypair = 'yes'
        self._is_creating_eks = 'yes'
        
        self._vpc_id = None
        self._sg_ids = []
        self._keypair_name = None
    
        self._pem_path = None
        self._pem_full_path_name = None



        self._ec2_instance_id  = None
        self._ec2_public_ip = None
        self._image_id = "ami-0568773882d492fc8"
        self._instancetype= "t2.large"
        self._volume = 20
        self._ec2_name = None
  
        self._project = None
        self._tags = [
            {'Key': 'managedBy', 'Value': 'boto3'}
        ]
        self._run_process_files = "yes"
        self._delete_eks_cluster = "yes"
        self._ec2_action = None
        self._base_path = os.getcwd()
        self._config_dict = {}
        self._eks_config_dict = {}
        self._ec2_config_dict = {}

        self._is_remove_all_created_resources = "yes"


        self._is_confirmed = "no"
        self._is_process_default_files = "no"
        self._process_first_n_files = 1

        self._config_file = "config.yaml"
        self._ssh_command = ""
        self._sg_name = 'SSH-ONLY'

        self._ssh_total_wait_time = 60
        self._ssh_wait_time_interval = 2
        self._login_user ="ec2-user"
        self._eks_action = EKSAction.create.name
        self._instancetState = None
        self._is_update_config_folder = "yes"
        self._max_nodes = None
        self._project_folder = None
        self._starttime = str(int(time.time()))


        # gcd parameters
        self._code_block_folder = ""
        self._num_of_nodes = 1
        self._process_first_n_files = 1
        self._use_default_files = "no"
        self._data_bucket = ""
        self._saved_bucket = ""
        self._process_column_keywords =[]
        self._use_default_ec2_bastion = "yes"
        self._use_default_eks_cluster = "yes"
        # solver 
        self._solver_name = None
        self._solver_lic_local_path = None
        self._solver_lic_target_path = None
        self.solver_lic_file_local_source = None
        self._project_in_tags= None

        self._user_id = None

        self._cluster_name = None

        self._nodegroup_name = None        

        self._is_breaking_ssh = "no"
        self._export_ec2_config_file = None
        self._export_eks_config_file = None
        self._export_eks_config_file = None

        
        self._ec2_client = connect_aws_client(
                    client_name='ec2',
                    key_id=self.aws_access_key,
                    secret= self.aws_secret_access_key,
                    region=self.aws_region
                )

        self._ec2_resource = connect_aws_resource(
            resource_name='ec2',
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region
        )
        
        
        self.machine = Machine(model=self, states=HandleEC2Bastion.states, initial='system_stop', on_exception='handle_error',send_event=True)
        # create ec2 steps 
        self.machine.add_transition(trigger='trigger_initial', source='system_stop', dest='system_initial', after='handle_verify_input')
        self.machine.add_transition(trigger='trigger_resources_ready', source='system_initial', dest='cloud_resources_ready', after ='hanlde_create_cloud_resources')
        self.machine.add_transition(trigger='trigger_create_ec2', source='cloud_resources_ready', dest='ec2_ready', before ='handle_create_ec2', after="handle_install_dependencies")
        self.machine.add_transition(trigger='trigger_create_eks', source='ec2_ready', dest='eks_ready', before ='handle_eks_action')
        self.machine.add_transition(trigger='trigger_cleanup', source='*', dest='cleanup', before ='handle_cleanup', after = 'handle_export_to_file')

        # ssh steps  (create_eks, delete_eks, run-files)

        self.machine.add_transition(trigger='trigger_ssh', source='system_stop', dest='ec2_ready',after='handle_ssh_coonection')
 

    def testing_fun(self):


        # code_template_folder = config_json['worker_config']['code_template_folder']
        # local_dir = f"./config/{code_template_folder}"
        # localpath , file = os.path.split(cluster_file)
        # remote_dir=f"{remote_base_path}"

        # ssh_upload_folder_to_ec2(
        #     ec2_client=ec2_client,
        #     user_name=user_name,
        #     instance_id=ec2_instance_id,
        #     pem_location=pem_file,
        #     local_folder=local_dir,
        #     remote_folder=remote_base_path
        # )
        # ic = get_ec2_instance_id_and_keypair_with_tags(
        #     ec2_client=self._ec2_client,
        #     tag_key_f="Name",
        #     tag_val_f="hellow"
        # )
        # print(ic)
        # ic2 = get_ec2_instance_id_and_keypair_with_tags(
        #     ec2_client=self._ec2_client,
        #     tag_key_f="Name",
        #     tag_val_f="gcd-solar"
        # )
        # print(ic2)
        # testing
        # vpci_id =get_default_vpc_id(ec2_client=self._ec2_client)
        # print(vpci_id)
        # self._keypair_name = "JL-2"
        # check_keypair_exist(ec2_client=self._ec2_client, keypair_anme=self._keypair_name)
        logging.info("-------------------")
        logging.info(f"upload config folder")
        logging.info("-------------------")
        self._pem_full_path_name = '/Users/jimmyleu/.ssh/gcd-key-jimmysmacbookpro2local.pem'
        
        self._ec2_instance_id = "i-057574d54500e5631"
        local_folder= '/Users/jimmyleu/Development/gismo/gismo-cloud-deploy/gismoclouddeploy/services/projects/solardatatools'
        project_folder = basename(local_folder)
 
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services/projects"
        local_files_list = get_all_files_in_local_dir(local_dir=local_folder)
        # parent = Path(r'/a/b')
        # son = Path(r'/a/b/c/d')  
        # print(son.relative_to(parent)) # returns Path object equivalent to 'c/d'
        
        # for file in local_files_list:
        #     path, filename = os.path.split(file)
        #     relative = Path(path).relative_to(Path(local_folder))
        #     print(relative)
        #      print(file,local_folder)
        #      print(relative_path)
        #      print("------------")
        ssh_upload_folder_to_ec2(
            user_name="ec2-user",
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_full_path_name,
            local_folder= local_folder,
            remote_folder=f"{remote_base_path}",
            ec2_resource=self._ec2_resource,

        )

        # check_keypair_name_exists(
        #     ec2_client=ec2_client,
        #     keypair_name="hello"
        # )

        return 

    def get_user_id(self) -> str:
        sts_client = connect_aws_client(
            client_name='sts',
            key_id= self.aws_access_key,
            secret= self.aws_secret_access_key,
            region=self.aws_region
        )
        user_id = get_iam_user_name(
            sts_client=sts_client
        )
        return user_id
        # host_name = (socket.gethostname())
        # user_id  = re.sub('[^a-zA-Z0-9]', '', host_name).lower()
        # return user_id



    def handle_import_configfile(self):
        logging.info("Handle import config files")
        if self._user_id is None:
            self._user_id = self.get_user_id()
        # step 1 enter project folder
        # -------------------
        # File structure
        #---------------------
        default_project = self._base_path +"/projects/solardatatools"
        project_path = handle_input_project_path_question(
            input_question="Enter project folder (Hit `Enter` button to use default path",
            default_answer=default_project
        )
        # while True:
        #     project_path = str(input(f"Enter project folder (Hit `Enter` button to use default path:{default_project} path): ") or default_project)
        #     test = re.findall("\'(.*?)\'",project_path)
         
        #     if not os.path.exists(project_path):
        #         raise Exception(f"project path: {project_path} does not exist!!")
        #     else:
        #         break
  
        self._project_full_path = project_path
        self._project_folder = basename(project_path)
        print(self._project_folder)

        # check if config file exists

        self._config_file = self._project_full_path + "/config.yaml"
        if not exists(self._config_file):
            raise Exception(f"config.yaml: {self._config_file} does not exist!!")
        try:
            self._config_dict= convert_yaml_to_json(yaml_file=self._config_file)
        except Exception as e:
            raise Exception(f"convert config yaml failed")
        verify_keys_in_configfile(self._config_dict)
        logging.info("config.yaml exists, verify input success")
        # check entrypoint folder and entrypoint.py exists
        # entrypoint_path = self._project_full_path +"/entrypoint"
        # if not os.path.exists(entrypoint_path):
        #     raise Exception(f"Entrypoint driecrory: {entrypoint_path} does not exist!!")
        # entrypoint_file = entrypoint_path +"/entrypoint.py"
        entrypoint_file = self._project_full_path + "/entrypoint.py"
        if not exists(entrypoint_file):
            raise Exception(f"entrypoint.py: {entrypoint_file} does not exist!!")
        logging.info("entrypoint.py exists")

        docker_file = self._project_full_path + "/Dockerfile"
        if not os.path.exists(docker_file):
            raise Exception(f"Dockerfile: {docker_file} does not exist!!")
        logging.info("Dockerfile exists")

        requirements = self._project_full_path + "/requirements.txt"
        if not os.path.exists(requirements):
            raise Exception(f"requirements.txt: {requirements} does not exist!!")
        logging.info("requirements.txt exists")
        # -------------------
        # EC2
        #---------------------


        # step 2 ec2 config file
        ec2_config_file = None
        if self._ec2_action == EC2Action.start.name:
            ec2_config_file = self._base_path +"/config/ec2/config-ec2.yaml"
            # create ec2 path 
            ec2_path = self._project_full_path + "/ec2"
            if not os.path.exists(ec2_path):
                os.makedirs(ec2_path)
        else:
            ec2_config_file = self._project_full_path +"/config-ec2.yaml"
        if not exists(ec2_config_file):
            raise Exception(f"EC2 config file : {ec2_config_file} does not exist!!")
        self._ec2_config_file = ec2_config_file
        self._ec2_config_dict = convert_yaml_to_json(yaml_file=self._ec2_config_file)

        home_path = str(Path.home())
        self._pem_path = home_path +"/.ssh"
      
        # ec2 prarmeters
        self._login_user = self._ec2_config_dict['login_user']
        if self._ec2_action != EC2Action.start.name:
        # chcek ec2 status  
            self._ec2_instance_id = self._ec2_config_dict['ec2_instance_id']
            self._keypair_name = self._ec2_config_dict['key_pair_name']
            # check if pem file exist
            self._pem_full_path_name = self._pem_path +f"/{self._keypair_name}.pem"
            print(f"self._pem_full_path_name {self._pem_full_path_name}")
            if not exists(self._pem_full_path_name):
                raise Exception (f"Key file {self._pem_full_path_name} does not exist")
        else:
            self._keypair_name = f"gcd-key-{self._user_id}"
            self._ec2_name = f"gcd-{self._user_id}-{self._starttime}"
            self._tags.append({'Key':'Name','Value':self._ec2_name })
            if not os.path.exists(self._pem_path):
                os.makedirs(self._pem_path)
       
        
        
        # while True:
        #     pem_file_path = str(input(f"Enter the pem path (hit enter to use default path: {self._pem_full_path_name }): ") or self._pem_full_path_name )
        #     if not os.path.exists(pem_file_path):
        #         logging.debug(f"{pem_file_path} does not exist")

        #     else:
        #         break


        # self._keypair_download_path = pem_file_path
        
        # logging.info(f"pem file : {self._keypair_download_path}")
        # full_pem =  self._keypair_download_path + f'/{self._keypair_name}.pem'
        # logging.info(f"pem file and path : {full_pem}")
        # self._pem_full_path_name = full_pem
        
        # logging.info(f"ec2 config file :{self._ec2_config_file}")


 
        # ec2_resource = connect_aws_resource('ec2', key_id=self.aws_access_key, secret=self.aws_secret_access_key, region=self.aws_region)
        # ec2_client = connect_aws_client('ec2', key_id=self.aws_access_key, secret=self.aws_secret_access_key, region=self.aws_region)
        # check ec2 status
        # response = self._ec2_client.describe_instance_status(
        #     InstanceIds=[self._ec2_instance_id],
        #     IncludeAllInstances=True
        # )
        # print(f"response : {response}")
        # for instance in response['InstanceStatuses']:
        #     instance_id = instance['InstanceId']
        #     if instance_id == self._ec2_instance_id:
            
        #         system_status = instance['SystemStatus']
        #         instance_status = instance['InstanceStatus']
        #         self._instancetState = instance['InstanceState']
        #         # logging.info(f"system_status :{system_status}, instance_status:{instance_status},")
        # if  self._instancetState is not None:
        #     logging.info(f"instance state : { self._instancetState}")
        # else:
        #     raise Exception(f"Cannot find instance state from {self._ec2_instance_id}")

        # -------------------
        # EKS
        #---------------------
        # step3 eks config file
        eks_config_file = None
        if self._ec2_action == EC2Action.start.name:
            eks_config_file = self._base_path +"/config/eks/cluster.yaml"
            # create ec2 path 
           
            eks_path = self._project_full_path + "/eks"
            if not os.path.exists(eks_path):
                os.makedirs(eks_path)
        else:
             eks_config_file = self._project_full_path +"/cluster.yaml"
        if not exists(eks_config_file):
            raise Exception(f"EKS config file : {eks_config_file} does not exist!!")

        self._eks_configfile = eks_config_file
        self._eks_config_dict = convert_yaml_to_json(yaml_file=self._eks_configfile)
        if self._ec2_action == EC2Action.start.name:
            self._cluster_name = f"gcd-{self._user_id}-{self._starttime}"
            self._nodegroup_name = f"gcd-{self._user_id}-{self._starttime}" 
        else:
            self._cluster_name = self._eks_config_dict['metadata']['name']
            self._nodegroup_name = self._eks_config_dict['nodeGroups'][0]['name']
            self._project_in_tags = self._eks_config_dict['metadata']['tags']['project']
        print(f"self._user_id :{self._user_id}")
        print(f"self._keypair_name : {self._keypair_name}")
        print(f"self._cluster_name : {self._cluster_name}")

    def change_config_parameters_from_input(self):
        logging.info("change_config_parameters_from_input")
        # step 1 
        if self._ec2_action == EC2Action.cleanup_resources.name:
            logging.info("Clean up resource. No input needed")
            return


        # question 1 destroy resources after completion?
        logging.info("question. clean up cloud resources after completion")
        # return boolean
        self._is_remove_all_created_resources = handle_yes_or_no_question(
            input_question="Is clean all created cloud resources after completioon? ",
            default_answer="yes"
        )
        logging.info(f"Clean up created cloud resources : {self._is_remove_all_created_resources}")



        # question 2 change config parametes ?
        logging.info("Project name")
        self._project_in_tags = hanlde_input_project_name_in_tag(
            input_question="Enter the name of project. This will be listed in all created cloud resources, and it's used for managing budege. (It's not the same as project path)",
            default_answer = self._project_in_tags
    
        )
        # update tag 
        self._tags.append({'Key':'project', 'Value':self._project_in_tags})

        if self._ec2_action == EC2Action.ssh.name:
            logging.info("Running ssh command. No input questions")
            return 


       
        


        # is_changing_default_config_file = handle_yes_or_no_question(
        #     input_question="Do you want to change parameters of default config.yaml file? ",
        #     default_answer="no"
        # )
       
        # logging.info(f"Change parameters of default config.yaml : {is_changing_default_config_file}")
        
        # if is_changing_default_config_file is True:
            # self._data_bucket = self._config_dict['worker_config']['data_bucket']
            # self._saved_bucket = self._config_dict['worker_config']['save_bucket']
        self._handle_config_inputs()
        

    def _handle_config_inputs(self):
        logging.info("handle config inputs")


        # question 4 use default file 
        is_process_default_file  = handle_yes_or_no_question(
            input_question=f"Do you want to process the defined files in config.yaml?",
            default_answer="no"
        )
        if is_process_default_file is False:
                
            handle_input_number_of_process_files_question(
                input_question="How many files you would like process? \n Input an postive integer number. \n Input '0' to process all files in the data bucket \n Otherwise, It processes first 'n'(as input) number files.",
                default_answer=1,
            )
        else:
            self._process_first_n_files = None
            logging.info("Process default files")
        
        logging.info("question 3. input the number of instances ")
        if len(self._eks_config_dict['nodeGroups'])>0 :

            self._max_nodes = self._eks_config_dict['nodeGroups'][0]['maxSize']
            self._num_of_nodes = handle_input_number_of_scale_instances_question(
                input_question="How many instances you would like to generate to run this application in parallel? \n Input an postive integer: ",
                default_answer=1,
                max_node= self._max_nodes
            )
        else:
            raise ValueError(f"Parse eks clust.yaml failed. No nodegroup")
        logging.info(f"Number of generated instances:{self._num_of_nodes}")
    
       

    def prepare_ec2(self):
        logging.info("Prepare ec2 action")
        if self._ec2_action == EC2Action.start.name:
            logging.info("Start a new process. create ec2.")
        else:
            logging.info(f"Import from existing .yaml file action: {self._ec2_action}")
        
        self._project_folder =  basename(normpath(self._project_full_path))
        logging.info("Ask for confirmation")
        number_process_files = str(self._process_first_n_files)
        if self._process_first_n_files is None:
            number_process_files = "Default files"
            self._ssh_command = f"python3 main.py run-files -s {self._num_of_nodes} -p {self._project_folder}"
        # separate project folder 
       

        self._ssh_command = f"python3 main.py run-files -n {self._process_first_n_files} -s {self._num_of_nodes} -p {self._project_folder}"

        if self._ec2_action == EC2Action.start.name:

            cloud_resource = [
                ["Parameters","Details"],
                ['project full path', self._project_full_path],
                ['project folder', self._project_folder],
                ['number of process files', number_process_files],
                ['number of  generated instances', self._num_of_nodes],
                ['max nodes size',self._max_nodes],
                ["cleanup cloud resources after completion",self._is_remove_all_created_resources],
                ["EC2 bastion name",self._ec2_name],
                ["SSH command", self._ssh_command],
                ["EKS cluster name",self._cluster_name],
                ['poject in tags',self._project_in_tags],
            ]
        else:
            self._instancetState = get_ec2_state_from_id(
                ec2_client=self._ec2_client,
                id = self._ec2_instance_id
            )
            cloud_resource = [
                ["Parameters","Details"],
                ['project full path', self._project_full_path],
                ['project folder', self._project_folder],
                ['number of process files', number_process_files],
                ['number of  generated instances', self._num_of_nodes],
                ['max nodes size',self._max_nodes],
                ["cleanup cloud resources after completion",self._is_remove_all_created_resources],
                ["EC2 bastion name",self._ec2_name],
                ["EC2 id",self._ec2_instance_id],
                ["EC2 state",self._instancetState],
                ["SSH command", self._ssh_command],
                ["EKS cluster name",self._cluster_name],
                ["EKS group name",self._nodegroup_name],
                ['poject in tags',self._project_in_tags],
            ]

        table1 = AsciiTable(cloud_resource)
        print(table1.table)

        self._is_confirmed = handle_yes_or_no_question(
            input_question="Comfim to process (must be yes/no)",
            default_answer="yes"
        )
        
         


    def handle_ssh_coonection(self):
        logging.info("Handle ssh connection")
        if self._ec2_instance_id is None or self._instancetState is None: 
            logging.error("Something wrong , no ec2 id or instance state")
            return 

        if not exists(self._pem_full_path_name):
            logging.error(f"Pem file:{self._pem_full_path_name} does not exist")
            return

        try:

            res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).start() #for start an ec2 instance
            logging.info(res)
        except Exception as e:
            raise Exception (f" start instacne error :{e}")
        try:
            is_connection = check_if_ec2_ready_for_ssh(
                instance_id=self._ec2_instance_id, wait_time=60, delay=5,
                pem_location= self._pem_full_path_name,
                user_name=self._login_user)
        except Exception as e:
            raise Exception(f"ssh connection error: {e}")
        if is_connection is False:
            raise Exception(f"ssh to  {self._ec2_instance_id} connection failed  ")


        return 

    def handle_ssh_update(self):
        
        is_update = handle_yes_or_no_question(
            input_question="Do you want to update cloud project folder from local project folder?",
            default_answer="yes"
        )
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
        remote_projects_folder = remote_base_path + f"/projects"
        if is_update is True:

            logging.info("-------------------")
            logging.info(f"upload local project folder to ec2 projects")
            logging.info(f"local folder:{self._project_full_path}")
            logging.info(f"remote folder:{remote_projects_folder}")
            logging.info("-------------------")
        

            ssh_upload_folder_to_ec2(
                user_name=self._login_user,
                instance_id=self._ec2_instance_id,
                pem_location=self._pem_full_path_name,
                local_folder=self._project_full_path,
                remote_folder=remote_projects_folder,
                ec2_resource=self._ec2_resource,

            )
        else:
            logging.info("Skip update")
        return 

    def set_breaking_ssh(self):

        inst_question = [
            inquirer.List('is_breaking',
                            message="breaking ssh ?",
                            choices=['yes','no'],
                        ),
        ]
        inst_answer = inquirer.prompt(inst_question)

        self._is_breaking_ssh = inst_answer["is_breaking"]
        logging.info(f"Breaking ssh: {self._is_breaking_ssh}")

    def get_breaking_ssh(self) -> bool:
        if self._is_breaking_ssh == "yes":
            return True
        else:
            return False

    def handle_error(self, event):
        logging.error("Handle error")
        raise ValueError(f"Oh no {event.error}") 
        
    
    def is_confirm_creation(self) -> bool:
        return self._is_confirmed

    def set_ec2_action(self):
        inst_question =[]
        if self._ec2_action is None:
            logging.info("Set EC2 action Create, running, stop, terminate, ssh")
            inst_question = [
                inquirer.List('action',
                                message="Select action type ?",
                                choices=[
                                    EC2Action.start.name,
                                    EC2Action.activate_from_existing.name, 
                                    EC2Action.cleanup_resources.name, 
                                    EC2Action.ssh.name],
                            ),
            ]
 
        else: 
            logging.info(f"Prvious ec2 action state {self._ec2_action}")
            logging.info("Set EC2 action Create, start, stop, terminate, ssh")
            inst_question = [
                inquirer.List('action',
                                message="Select action type ?",
                                choices=[EC2Action.start.name, EC2Action.activate_from_existing.name,EC2Action.cleanup_resources.name, EC2Action.ssh.name],
                            ),
            ]

        inst_answer = inquirer.prompt(inst_question)
        self._ec2_action = inst_answer["action"]
           
        logging.info(f"Set ec2 action : {self._ec2_action}")


    def get_ec2_action(self):
        return  self._ec2_action


        

    def handle_ec2_action(self):

        if self._ec2_instance_id is None: 
            self.handle_import_configfile(self)
          

        if self._ec2_action == EC2Action.running.name:
            logging.info("Start ec2 ")
            try:
                res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).start() #for start an ec2 instance
                instance = check_if_ec2_ready_for_ssh(instance_id=self._ec2_instance_id, wait_time=60, delay=5, pem_location=self._pem_full_path_name,user_name=self._login_user)

                public_ip = get_public_ip(
                    ec2_client=self._ec2_client,
                    instance_id=self._ec2_instance_id
                )
                logging.info("------------------")
                logging.info(f"public_ip :{public_ip}")
                logging.info("------------------")

            except Exception as e:
                raise Exception(f"Start ec2 failed: {e}")
            logging.info("Start instance success")
        elif self._ec2_action == EC2Action.stop.name:
            logging.info("Stop ec2")
            try:
                res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).stop() #for start an ec2 instance
                logging.info("Stop instance success")
            except Exception as e:
                raise Exception(f"Terminate ec2 failed: {e}")
        elif self._ec2_action == EC2Action.terminate.name:
            logging.info("Terminate ec2")
            try:
                res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).terminate() #for start an ec2 instance
                logging.info("Terminate instance success")
            except Exception as e:
                raise Exception(f"Terminate ec2 failed: {e}")
        else:
            logging.error("Unknow action")

        return 
    def set_vpc_info(self):
        logging.info("Set VPC")
         # VPC input
        while True:
            self._use_deafualt_vpc = str(input(f"Use default VPC ?(default:{self._use_deafualt_vpc}) (must be yes/no):") or self._use_deafualt_vpc)
            if self._use_deafualt_vpc.lower() not in ('yes', 'no'):
                print("Not an appropriate choice. please type 'yes' or 'no' !!!")
            else:
                break
        if self._use_deafualt_vpc == "no":
            self._vpc_id = input("Enter existing vpc id: ")
            logging.info(f"Input VPC id: {self._vpc_id}")
            logging.info(f"Checking VPC id:{self._vpc_id}")
        else:
            print(f"Use default vpc")
    

    
    # def set_security_group_info(self):
    #     logging.info("Set security group info")
    #     # security group input 
    #     while True:
    #         self._is_creating_sg = str(input(f"Create a new security group allow SSH connection only ?(default:{self._is_creating_sg}) (must be yes/no):") or self._is_creating_sg)
    #         if self._is_creating_sg.lower() not in ('yes', 'no'):
    #             print("Not an appropriate choice. please type 'yes' or 'no' !!!")
    #         else:
    #             break
    
    #     if self._is_creating_sg == "no":
    #         sg_id = input("Enter existing security group id: ")
    #         logging.info(f"security group id: {self._sg_ids.append(sg_id)}")
    #         logging.info(f"Checking security group id:{self._sg_ids}")

    #     else:
    #         print(f"Create a new security group")

       
        
    # def set_keypair_info(self):
    #     logging.info("Set keypair info")
    #     while True:
    #         self._is_creating_keypair =  str(input(f"Create a new keypair ?(default:{self._is_creating_keypair}) (must be yes/no):") or self._is_creating_keypair)
    #         if self._is_creating_keypair.lower() not in ('yes', 'no'):
    #             print("Not an appropriate choice. please type 'yes' or 'no' !!!")
    #         else:
    #             break
    #      # Key pair input
    #     if self._is_creating_keypair == "no":
    #         while True:
    #             self._keypair_name = input("Enter existing keypair name: ")
    #             if len(self._keypair_name) < 2:
    #                 logging.error(f"Keypair name is too short: {self._keypair_name}")
    #             else:
    #                 break
    #         print(f"key pair name: {self._keypair_name }")
    #     else:
    #         while True:
    #             self._keypair_name  = input("Enter a new keypair name: ")
    #             if len(self._keypair_name) < 2:
    #                 logging.error(f"Keypair name is too short: {self._keypair_name}")
    #             else:
    #                 break
    #         print(f"Creating keypair: {self._keypair_name }")
    #     self._keypair_download_path = os.getcwd() + "/config/keypair"

    #     while True:
    #         download_path = str(input(f"Enter the pem path (hit enter to use default path: {self._keypair_download_path }): ") or self._keypair_download_path )
    #         if not os.path.exists(download_path):
    #             logging.debug(f"{download_path} does not exist")

    #         else:
    #             break
    #     self._keypair_download_path = download_path


       
    # def set_ec2_info(self):
    #     logging.info("Set ec2 info")
    #     while True:
    #         self._ec2_name = input("Creat a EC2 name  :") 
    #         if len(self._ec2_name) < 2:
    #             logging.error(f"ec2 name is too short: {self._ec2_name}")
    #         else:
    #             break
    #     print(f"EC2 name : {self._ec2_name }")
    #     self._tags.append({'Key': 'Name', 'Value': self._ec2_name})
    #     while True:
    #         self._project = input("Creat a project name in tag:") 
    #         if len(self._project) < 2:
    #             logging.error(f"project name is too short: {self._project}")
    #         else:
    #             break
    #     print(f"Project name : {self._project }")
    #     self._tags.append({'Key': 'project', 'Value': self._project})
    #     # instance type
    #     inst_question = [
    #         inquirer.List('instance_type',
    #                         message="Select instance type (suggest 't2.large')?",
    #                         choices=['t2.large','t2.medium','t2.xlarge'],
    #                     ),
    #     ]
    #     inst_answer = inquirer.prompt(inst_question)
    #     logging.info (inst_answer["instance_type"])
    #     self._instancetype= inst_answer["instance_type"]

    #     ec2_volume = str(input(f"Enter the ec2 volume (enter for default: {self._volume}): ") or self._volume)
    #     self._volume = ec2_volume
    #     logging.info(f"Input volume: { self._volume}")
    #     basepath = os.getcwd()
    #     while True:
    #         export_file = str(input(f"Enter the export file name (enter for default:{self._ec2_config_file}): ") or self._ec2_config_file)
    #         name, extenstion = export_file.split(".")
    #         logging.info(f"Export file:{export_file}")
            
    #         if extenstion != "yaml":
    #             logging.error("file extension is not yaml")
    #         # if not exists(fullpath):
    #         #     logging.error(f"{fullpath} does not exist")
    #         else:
    #             break
        
    #     fullpath = self._base_path +f"/config/ec2/{export_file}"
    #     self._ec2_config_file = fullpath
        
    #     print(f"self._ec2_config_file :{self._ec2_config_file}")

        # running, stopped,or terminate after completion.
        # action_questions = [
        #     inquirer.List('action',
        #                     message="Select an action after process completed ?",
        #                     choices=[EC2Action.running.name,EC2Action.stop.name, EC2Action.terminate.name],
        #                 ),
        # ]
        # inst_answer = inquirer.prompt(action_questions)
        
        # self._ec2_action = inst_answer["action"]
        # if self._ec2_action == EC2Action.terminate.name:
        #     while True:
        #         self._is_remove_all_created_resources = str(input(f"Is removeall created resource after terminate ec2? {self._is_remove_all_created_resources }): ") or self._is_remove_all_created_resources )
        #         if self._is_remove_all_created_resources.lower() not in ('yes', 'no'):
        #             print("Not an appropriate choice. please type 'yes' or 'no' !!!")
        #         else:
        #             break
        #     print(f"Remove all created resources : {self._is_remove_all_created_resources}")
            

    # def set_eks_cluster_info(self):
    #     logging.info("Set eks cluster info")
    #     # create eks cluster
    #     while True:
    #         self._is_creating_eks =  str(input(f"Create a new eks cluster ?(default:{self._is_creating_eks}) (must be yes/no):") or self._is_creating_eks)
    #         if self._is_creating_eks.lower() not in ('yes', 'no'):
    #             print("Not an appropriate choice. please type 'yes' or 'no' !!!")
    #         else:
    #             break

    #     # import clustr config
    #     if  self._is_creating_eks == "yes":
    #         while True:
    #             eks_configfile = str(input(f"Enter the eks cluster file name (default:{self._eks_configfile}): ") or self._eks_configfile)
    #             name, extension = eks_configfile.split(".")
    #             logging.info(f"Create eks cluster from file:{eks_configfile}")
    #             if extension != "yaml":
    #                 logging.error(f"{name}.{extension} is not a yaml file!!")
               
    #             eksfullpath = self._base_path +f"/config/eks/{eks_configfile}"
    #             if not os.path.exists(eksfullpath):
    #                 logging.error(f"{eksfullpath} does not exist. Please try again!! (under path: {self._base_path}/config/eks/ )")
    #             else:
    #                 break
    #         self._eks_configfile = eksfullpath
    #         # delete cluter at end 
    #         while True:
    #             self._delete_eks_cluster = str(input(f"Delete EKS after completion?(default:{self._delete_eks_cluster}) (must be yes/no):") or self._delete_eks_cluster)
    #             if self._delete_eks_cluster.lower() not in ('yes', 'no'):
    #                 print("Not an appropriate choice. please type 'yes' or 'no' !!!")
    #             else:
    #                 break

    def set_runfiles_command(self):
        logging.info("Set runfile command after eks cluster ready")
        basepth = os.getcwd()
        
        while True:
            
            file  =  str(input(f"Enter system config file name (default:{self._config_file}): ") or self._config_file)
            full_path_and_name = basepth + f'/config/{file}'
            if not exists(full_path_and_name):
                logging.error(f"{full_path_and_name} does not exist")
            else:
                break
        self._config_file = full_path_and_name
        while True:
            self._is_process_default_files = str(input(f"Is prossing the default files list in config.yaml (must be yes/no )(default:{self._is_process_default_files}): ") or self._is_process_default_files)
            if self._is_process_default_files.lower() not in ('yes', 'no'):
                print("Not an appropriate choice. please type 'yes' or 'no' !!!")
            else:
                break
            print(f"Is prossing the default files list in {self._config_file} :{self._is_process_default_files}")
        if self._is_process_default_files == "no":
            while True:
                try:
                    self._process_first_n_files = int(input(f"Process the fist n files (must an integer). Enter 0 to process all files in the data bucket. (default:{self._process_first_n_files}): ") or self._process_first_n_files)
                except Exception as e:
                    print(f"Input is not an integer use default value {self._process_first_n_files}")
                if self._process_first_n_files < 0 :
                    print("Cannot be a negative intger")
                else:
                    break
            print(f"Process the first {self._process_first_n_files} files.(If input is 0, process all files in the data bucket)")
            self._ssh_command = f"python3 main.py run-files -n {self._process_first_n_files} -b -d"
        


    def handle_verify_input(self, event):
        logging.info("Handle cloud resources input")

        # VPC ID 
        if self._use_deafualt_vpc == "yes":
                logging.info("Use default vpc")
                self._vpc_id = get_default_vpc_id(ec2_client=self._ec2_client)
        else:     
            logging.info(f"Checking VPC : {self._vpc_id}")
            if not check_vpc_id_exists(ec2_client=self._ec2_client, vpc_id= self._vpc_id):
                logging.error(f"Cannot find vpc id {self._vpc_id}")
                return 


        # Check security group 
        if self._is_creating_sg == "yes":
            logging.info(f"Checking security group  : {self._sg_ids}")
            sg_id = check_sg_group_name_exists_and_return_sg_id(
                ec2_client= self._ec2_client,
                group_name=self._sg_name,
            )
            if sg_id is not None:
                self._sg_ids.append(sg_id)
                logging.info(f"Find and use existing sercurity group id :{self._sg_ids }")
                self._is_creating_sg = "no"
            # if self._sg_id is not None:
            #     logging.info(f"Find and use existing sercurity group id :{self._sg_id }")
            #     self._is_creating_sg = "no"

        #Check key pair
        if self._is_creating_keypair == "no":
            logging.info(f"Checking key pair  : {self._keypair_name}")
            if not check_keypair_name_exists(
                ec2_client=self._ec2_client,
                keypair_name=self._keypair_name):
                logging.error(f"Cannot find keypair: {self._keypair_name}")
                return 
        
        
        cloud_resource = [
			["Parameters","Details"],
            ['project', self._project],
			["Use default VPC", self._use_deafualt_vpc, self._vpc_id ],
			["Create security group",self._is_creating_sg, self._sg_ids],
			["Create a new keypair",self._is_creating_keypair, self._keypair_name],
            ["Keypair download path",self._pem_path],
            ["Image id",self._image_id],
            ["Instance type",self._instancetype],
            ["volume",self._volume],
            ["Name",self._ec2_name],
            ["Project",self._project],
            ['EKS cluster file', self._eks_configfile],
            ['Config file', self._config_file],
            ["Export file name",self._ec2_config_file],
            ["SSH Command",self._ssh_command],
            ["EC2 status after completion",self._ec2_action],
            ['Delete EKS cluster after completion',  self._delete_eks_cluster],
            ["Remove created resources",self._is_remove_all_created_resources]

	    ] 

        table1 = AsciiTable(cloud_resource)
        print(table1.table)

            
        while True:
            self._is_confirmed = input("Comfim to process creation (must be yes/no):")
            if  self._is_confirmed.lower() not in ('yes', 'no'):
                print("Not an appropriate choice. please type 'yes' or 'no' !!!")
            else:
                break
        if  self._is_confirmed == 'no':
            logging.info("Cancel create ec2 bastion !!")
            return 


    
    def hanlde_create_cloud_resources(self):
        logging.info("Handle create resources")

        if self._ec2_action == EC2Action.start.name:
            # get default vpc id
            vpc_id = get_default_vpc_id(ec2_client=self._ec2_client)
            if vpc_id is not None:
                self._vpc_id = vpc_id
            else:
                raise Exception("No default vpc id found")
            # check security group name 
            sg_id = get_security_group_id_with_name(ec2_client=self._ec2_client, group_name=self._sg_name)

            if sg_id is None:
                security_info_dict = create_security_group(
                        ec2_client=self._ec2_client,
                        vpc_id=self._vpc_id,
                        tags=self._tags,
                        group_name=self._sg_name
                    )
                self._sg_ids = [security_info_dict['security_group_id']]
                logging.info(f"Create SecurityGroupIds : {self._sg_id} in vpc_id:{self._vpc_id} success")
            else:
                logging.info(f"Found security groupd with name: {self._sg_name}  id: {sg_id}")
                self._sg_ids = [sg_id]
            


        # Create Key pair
        if not check_keypair_exist(ec2_client=self._ec2_client, keypair_anme=self._keypair_name):
            logging.info(f"keypair:{self._keypair_name} does not exist create a new keypair")
            create_key_pair(ec2_client=self._ec2_client, keyname=self._keypair_name, file_location=self._pem_path)
        else:
            logging.info(f"keypair:{self._keypair_name} exist")
        # if self._is_creating_keypair == "yes":
        #     try:
                
        #     except Exception as e:
        #         logging.error(f"Create key pair error :{e}")
        #         raise e
        self._export_ec2_config_file = self._project_full_path +"/config-ec2.yaml"
        self._export_eks_config_file = self._project_full_path +"/cluster.yaml"

        instance_info = get_ec2_instance_id_and_keypair_with_tags(
            ec2_client=self._ec2_client,
            tag_key_f="Name",
            tag_val_f=self._ec2_name
        )
        if instance_info is not None:
            id = instance_info['InstanceId']
            keyname = instance_info['KeyName']
            state = instance_info['State']['Name']
            logging.warning(f"EC2 {self._ec2_name} exists, {instance_info}")
            if keyname != self._keypair_name:
                # logging.error(f"{instance_info} has different keypair from {self._keypair_name} ")
                raise Exception (f"{instance_info} has different keypair from {self._keypair_name} ")
            else:
                logging.warning ("Existing ec2 instance")
                if state == 'terminated':
                    logging.warning ("Previous ec2 instance in terminated state, rename ec2 Name")
                    self._ec2_name = f"{self._ec2_name}-{self._starttime}"
                    for tags in self._tags:
                        if tags['Key'] =='Name':
                            tags['Value'] = self._ec2_name
                else:
                    logging.warning (f"Previous ec2 instance in {state} state, start {id}")
                    self._ec2_instance_id = id
                    self._ec2_action = EC2Action.activate_from_existing.name
              
        self._pem_full_path_name = self._pem_path +f"/{self._keypair_name}.pem"
        cloud_resource = [
			["Parameters","Details"],
            ['project', self._project_in_tags],
            ['project path', self._project_full_path],
			["Use default VPC", self._vpc_id ],
			["Create security group", self._sg_ids],
			["keypair", self._pem_full_path_name],
            ["EC2 Image id",self._image_id],
            ["EC2 name",self._ec2_name],
            ["Instance type",self._instancetype],
            ["volume",self._volume],
            ["Name",self._ec2_name],
            ['EKS cluster file', self._eks_configfile],
            ['Config file', self._config_file],
            ["Export ec2 file",self._export_ec2_config_file],
            ["Export eks file",self._export_eks_config_file],
            ["SSH Command",self._ssh_command],
            ["EC2 status after completion",self._ec2_action],
            ['Tags',self._tags],
            ["Remove created resources",self._is_remove_all_created_resources]

	    ] 
        table1 = AsciiTable(cloud_resource)
        print(table1.table)
        # export eks file
        update_and_export_eks_yaml(
            config_dict=self._eks_config_dict,
            export_file=self._export_eks_config_file,
            project=self._project_in_tags,
            cluster_name=self._cluster_name,
            aws_region=self.aws_region,
            nodegroup_name=self._nodegroup_name,
            max_nodes=self._max_nodes
        )
        # logging.info("export eks config")
        # self._eks_config_dict['tags'] = self._tags
        # self._eks_config_dict['metadata']['name'] = self._cluster_name
        # self._eks_config_dict['metadata']['region'] = self.aws_region

        # self._eks_config_dict['nodeGroups'[0]]['name'] = self._nodegroup_name
        # self._eks_config_dict['nodeGroups'[0]]['tags'] = self._tags
        # self._eks_config_dict['nodeGroups'[0]]['maxSize'] = self._max_nodes
        
        # write_aws_setting_to_yaml(
        #     file=self._export_eks_config_file, 
        #     setting=self._eks_config_dict
        # )
    
        # export 
        # print(f"self._image_id: {self._image_id}")
        # print(f"self._keypair_name,: {self._keypair_name,}")
        # print(f"self._sg_ids: {self._sg_ids}")
        # print(f"elf._volume: {self._volume}")
        # print(f"self._project_in_tags: {self._project_in_tags}")

        # check if ec2 already exist
        
        self._eks_config_dict
                
            
        return

    def handle_create_ec2(self):
        logging.info("Handle create ec2")

        try:
            ec2_instance_id = create_instance(     
                ImageId=self._image_id,
                InstanceType = self._instancetype,
                key_piar_name = self._keypair_name,
                ec2_client=self._ec2_client,
                tags= self._tags,
                SecurityGroupIds = self._sg_ids,
                volume=self._volume

            )
            logging.info(f"ec2_instance_id: {ec2_instance_id}")
            self._ec2_instance_id = ec2_instance_id
            logging.info("-------------------")
            logging.info(f"Create ec2 bastion completed")
            logging.info("-------------------")

        except Exception as e:
            raise Exception(f"Create ec2 instance failed {e}")



       
    

    def handle_install_dependencies(self):
        logging.info("Handle install dependencies")
        pem_file=self._pem_path +"/"+self._keypair_name+".pem"
        instance = check_if_ec2_ready_for_ssh(
            instance_id=self._ec2_instance_id , 
            wait_time=self._ssh_total_wait_time, 
            delay=self._ssh_wait_time_interval, 
            pem_location=pem_file,
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
        local_env = "./config/deploy/install.sh"
        remote_env="/home/ec2-user/install.sh"
        upload_file_to_sc2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=pem_file,
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
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            command=command,
            pem_location=pem_file,
            ec2_client=self._ec2_client
        )

        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
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
            pem_location=pem_file,
            ec2_client=self._ec2_client,
            local_file=local_env,
            remote_file=remote_env,
        )


        remote_projects_folder = remote_base_path + f"/projects"
        logging.info("-------------------")
        logging.info(f"upload local project folder to ec2 projects")
        logging.info(f"local folder:{self._project_full_path}")
        logging.info(f"remote folder:{remote_projects_folder}")
        logging.info("-------------------")
        

        ssh_upload_folder_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=pem_file,
            local_folder=self._project_full_path,
            remote_folder=remote_projects_folder,
            ec2_resource=self._ec2_resource,

        )
        # # upload solver
        # local_solver_file = "./config/license/mosek.lic"
        # remote_file=f"{remote_base_path}/config/license/mosek.lic"
        # logging.info("-------------------")
        # logging.info(f"upload solver")
        # logging.info("-------------------")
        # # # upload solver
        # upload_file_to_sc2(
        #     user_name=self._login_user,
        #     instance_id=self._ec2_instance_id,
        #     pem_location=pem_file,
        #     ec2_client=ec2_client,
        #     local_file=local_solver_file,
        #     remote_file=remote_file,
        # )

        # # upload eks config
        # eks_config_file = self._eks_configfile
        # path , file = os.path.split(eks_config_file)
        # remote_file=f"{remote_base_path}/config/eks/{file}"
        # logging.info("-------------------")
        # logging.info(f"upload eks clust config")
        # logging.info("-------------------")
        # # # upload solver
        # upload_file_to_sc2(
        #     user_name=self._login_user,
        #     instance_id=self._ec2_instance_id,
        #     pem_location=pem_file,
        #     ec2_client=ec2_client,
        #     local_file=local_solver_file,
        #     remote_file=remote_file,
        # )

        # export ec2 bastion setting to yaml
        ec2_json = {}
        ec2_json['SecurityGroupIds'] = self._sg_ids
        ec2_json['vpc_id'] =self._vpc_id
        ec2_json['ec2_instance_id'] =self._ec2_instance_id
        # ec2_json['public_ip'] = self._ec2_public_ip
        ec2_json['tags'] = self._tags
        ec2_json['ec2_image_id'] = self._image_id
        ec2_json['ec2_instance_type'] = self._instancetype
        ec2_json['ec2_volume']= self._volume
        ec2_json['key_pair_name'] = self._keypair_name
        ec2_json['login_user'] = self._login_user
        # ec2_json['pem_location'] = self._keypair_download_path

        logging.info("-------------------")
        logging.info(f"Export ec2 bastion setting to {self._export_ec2_config_file}")
        logging.info("-------------------")
        
        write_aws_setting_to_yaml(
            file=self._export_ec2_config_file, 
            setting=ec2_json
        )


    def set_eks_action(self, action):
        self._eks_action = action
        logging.info("-----------------------------")
        logging.info(f"ESK action: {self._eks_action}")
        logging.info("-----------------------------")
        # logging.info("Set EKS action")
        # inst_question = [
        #     inquirer.List('action',
        #                     message="Select eks action type ?",
        #                     choices=[EKSAction.create.name,EKSAction.delete.name, EKSAction.list.name, EKSAction.scaledownzero.name],
        #                 ),
        # ]
        # inst_answer = inquirer.prompt(inst_question)

        # self._eks_action = inst_answer["action"]

    def get_eks_action(self):
        return self._eks_action


    def ssh_update_config_folder(self):
        # test upload ec2 folder
        logging.info("Update config folder")
        inst_question = [
            inquirer.List('is_update',
                            message="Is update config folder?",
                            choices=['yes','no'],
                        ),
        ]
        inst_answer = inquirer.prompt(inst_question)

        logging.info (inst_answer["is_update"])

        self._is_update_config_folder= inst_answer["is_update"]
        if self._is_update_config_folder == "no":
            logging.info("No updating config folder")
            return 
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
    
        ssh_upload_folder_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_full_path_name,
            local_folder= "./config",
            remote_folder=f"{remote_base_path}",
            ec2_client=self._ec2_client,

        )
        logging.info("update config folder completed")
    #
    def set_and_run_ssh_command(self):
        logging.info("set and run  ssh command")
        self._ssh_command = input(f"Please type your command: ")
        logging.info(f"command : {self._ssh_command}")
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
        ssh_command = f"cd {remote_base_path} \n source ./venv/bin/activate\n export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env )  \n{self._ssh_command} "
       
        run_command_in_ec2_ssh(
            user_name= self._login_user,
            instance_id= self._ec2_instance_id,
            pem_location=self._pem_full_path_name,
            ec2_client=self._ec2_client,
            command=ssh_command
        )

        
    def get_ssh_command(self):
        return  self._ssh_command

    def import_ec2_info_from_config(self, config_file:str):
        self._ec2_config_file = config_file
        ec2_json = convert_yaml_to_json(yaml_file= self._ec2_config_file)
        
        self._keypair_name = ec2_json['key_pair_name']
        self._tags = ec2_json['tags']
        self._pem_path = ec2_json['pem_location']
        self._ec2_instance_id = ec2_json['ec2_instance_id']
        pem_file=self._pem_path  +"/"+self._keypair_name+".pem"
        self._login_user = ec2_json['user_name']

        # check instance id status
        
    


    
    def start_ec2(self):


        pem_file=self._pem_path  +"/"+self._keypair_name+".pem"
        if self._ec2_instance_id is not None:
            res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).start() #for stopping an ec2 instance
            instance = check_if_ec2_ready_for_ssh(instance_id=self._ec2_instance_id, wait_time=self._ssh_total_wait_time, delay=self._ssh_wait_time_interval, pem_location=pem_file,user_name=self._login_user)
            self._ec2_public_ip = get_public_ip(
                ec2_client=self._ec2_client,
                instance_id=self._ec2_instance_id
            )
            logging.info("---------------------")
            logging.info(f"public_ip :{self._ec2_public_ip}")
            logging.info("---------------------")

        else:
            logging.error("ec2_resource id is None")
            return
    
    def stop_ec2(self):

        if self._ec2_instance_id is not None:
            res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).stop() #for stopping an ec2 instance
            logging.info(f"Stop {self._ec2_instance_id} success")
            return
        else:
            logging.error("ec2_resource id is empty")
            return
    def terminate_ec2(self):
        
        logging.info("terminate ec2")

        if self._ec2_instance_id is not None:
            res = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).stop() #for stopping an ec2 instance
            res_term  = self._ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).terminate() #for terminate an ec2 insta
            
        else:
            logging.error("ec2_resource id is empty")
            return


    def handle_eks_action(self):
        logging.info("Handle eks action")
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
        remote_projects_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services/projects/{self._project_folder}"
        remote_cluster_file = remote_projects_path +"/cluster.yaml"
        # path, file  = os.path.split(self._eks_configfile)
        # remote_cluster_file=f"{remote_base_path}/config/eks/{file}"
        loca_eks_file = self._project_full_path + "/cluster.yaml"
        cluster_dict = convert_yaml_to_json(yaml_file=loca_eks_file)
        cluster_name = cluster_dict['metadata']['name']

        ssh_command_list = {}
        if self._eks_action == EKSAction.create.name:
            logging.info("set create eks culster command")
            command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl create cluster -f {remote_cluster_file}"
            ssh_command_list['Create EKS cluster'] = command

        elif self._eks_action == EKSAction.delete.name:
            logging.info("set delete eks culster command ")
            # scale down if cluster exist
            scaledown_command =  f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n rec=\"$(eksctl get cluster | grep {self._cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl scale nodegroup --cluster {self._cluster_name} --name {self._nodegroup_name} --nodes 0; fi"
            ssh_command_list['scaledonw cluster'] = scaledown_command
            # delete cluster if cluster exist
            delete_eks_command =  f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n rec=\"$(eksctl get cluster | grep {self._cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl delete cluster -f {remote_cluster_file}; fi"
            # delete_eks_command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl delete cluster -f {remote_cluster_file}"
            ssh_command_list['Delete EKS cluster'] = delete_eks_command
        elif self._eks_action == EKSAction.scaledownzero.name:
            #gcd-jimmy-cli-1663394353
            scale_down_command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n rec=\"$(eksctl get cluster | grep {self._cluster_name})\" \n if [ -n \"$rec\" ] ; then eksctl scale nodegroup --cluster {self._cluster_name} --name {self._nodegroup_name} --nodes 0; fi"

            ssh_command_list['Scale down nodes to 0'] = scale_down_command
        elif self._eks_action == EKSAction.list.name:
            logging.info("Run list command")
            command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl get cluster"
            ssh_command_list['List EKS cluster'] = command
        elif self._eks_action == EKSAction.runfiles.name:
            logging.info("Run files command")
            command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n cd /home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services/\n source ./venv/bin/activate \n python3 main.py run-files -s 1 -p {self._project_folder}"
            ssh_command_list['List EKS cluster'] = command
        for description, command in ssh_command_list.items():
            logging.info(description)
            run_command_in_ec2_ssh(
                    user_name=self._login_user,
                    instance_id=self._ec2_instance_id,
                    command=command,
                    pem_location=self._pem_full_path_name,
                    ec2_client=self._ec2_client
             )
        return 

    
        

    def handle_export_to_file(self, event):
        logging.info("Handle create eks cluster")

    def handle_cleanup(self):
        logging.info("Handle clean up")
        # step 1. delete eks
        # check eks exist


        self._eks_action = EKSAction.delete.name
        self.handle_eks_action()
        # step 2 . terminate ece
        self._ec2_action = EC2Action.terminate.name
        self.handle_ec2_action()
        # delte config-ec2, delete eks cluster
        if self._export_ec2_config_file is not None:
            try:
                os.remove(self._export_ec2_config_file)
                logging.info(f"Delete {self._export_ec2_config_file} success")
            except Exception as e:
                raise Exception(e)
        if self._export_eks_config_file is not None:
            try:
                os.remove(self._export_eks_config_file)
                logging.info(f"Delete {self._export_eks_config_file} success")
            except Exception as e:
                raise Exception(e)



def update_and_export_eks_yaml(
    config_dict: dict,
    export_file: str,
    project:dict,
    cluster_name:str,
    aws_region:str,
    nodegroup_name:str,
    max_nodes:int

) -> None:
    logging.info("export eks config")
    
    config_dict['metadata']['tags'] = {'project':project, 'managedBy':'eksctl'}
    config_dict['metadata']['name'] = cluster_name
    config_dict['metadata']['region'] = aws_region

    config_dict['nodeGroups'][0]['name'] = nodegroup_name
    config_dict['nodeGroups'][0]['tags'] = {'project':project, 'managedBy':'eksctl'}
    config_dict['nodeGroups'][0]['maxSize'] = max_nodes
    print(config_dict)
    write_aws_setting_to_yaml(
        file=export_file, 
        setting=config_dict
    )
    logging.info("Export eks config")