



from email.mime import base
from genericpath import exists
from re import S
from transitions import Machine
import os
import coloredlogs, logging
from terminaltables import AsciiTable
import inquirer
from .EC2Action import EC2Action
from .modiy_config_parameters import convert_yaml_to_json
from .check_aws import (
    connect_aws_client,
    check_environment_is_aws,
    connect_aws_resource,
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
)
from .EKSAction import EKSAction
coloredlogs.install()

class CreateEC2Bastion(object):
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
        
        self.aws_access_key =aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region


        self._use_deafualt_vpc = 'yes'
        self._is_creating_sg ='yes'
        self._is_creating_keypair = 'yes'
        self._is_creating_eks = 'yes'
        self._eks_configfile = 'cluster.yaml'
        self._vpc_id = None
        self._sg_ids = []
        self._keypair_name = None
        self._keypair_download_path = None
        self._pem_full_path_name = None
    

        self._ec2_instance_id  = None
        self._ec2_public_ip = None
        self._image_id = "ami-0568773882d492fc8"
        self._instancetype= "t2.large"
        self._volume = 20
        self._ec2_name = None
        self._ec2_config_file = 'config-ec2.yaml'
        self._project = None
        self._tags = [
            {'Key': 'managedBy', 'Value': 'boto3'}
        ]
        self._run_process_files = "yes"
        self._delete_eks_cluster = "yes"
        self._ec2_action = None
        self._basepath = os.getcwd()

        self._is_remove_all_created_resources = "no"


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

        self._is_breaking_ssh = "no"
        self._base_path = os.getcwd()
        
        
        self.machine = Machine(model=self, states=CreateEC2Bastion.states, initial='system_stop', on_exception='handle_error',send_event=True)
        # create ec2 steps 
        self.machine.add_transition(trigger='trigger_initial', source='system_stop', dest='system_initial', after='handle_verify_input')
        self.machine.add_transition(trigger='trigger_resources_ready', source='system_initial', dest='cloud_resources_ready', after ='hanlde_create_cloud_resources')
        self.machine.add_transition(trigger='trigger_create_ec2', source='cloud_resources_ready', dest='ec2_ready', before ='handle_create_ec2', after="handle_install_dependencies")
        self.machine.add_transition(trigger='trigger_create_eks', source='ec2_ready', dest='eks_ready', before ='handle_eks_action')
        self.machine.add_transition(trigger='trigger_cleanup', source='*', dest='cleanup', before ='handle_cleanup', after = 'handle_export_to_file')

        # ssh steps  (create_eks, delete_eks, run-files)

        self.machine.add_transition(trigger='trigger_ssh', source='system_stop', dest='ec2_ready',after='handle_ssh_coonection')
 

    def testing_fun(self):
        # testing
        ec2_client = connect_aws_client(
            client_name='ec2',
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region
        )
        # check_vpc_id_exists(
        #     ec2_client=ec2_client,
        #     vpc_id= "vpc-a27c77ca")
        # check_sg_group_name_exists_and_return_sg_id(
        #     ec2_client= ec2_client,
        #     group_name='SSH-ONLY',
        # )

        # check_keypair_name_exists(
        #     ec2_client=ec2_client,
        #     keypair_name="hello"
        # )

        return 

    def handle_import_configfile(self):
        logging.info("Handle import ec2 files")
        
        # step 1 get config input
        self._base_path = os.getcwd()
        while True:
            config_file = str(input(f"Enter the ec2 config file name (enter for default:{self._ec2_config_file}): ") or self._ec2_config_file)
            name, extenstion = config_file.split(".")
            logging.info(f"EC2 config file:{config_file}")
            
            if extenstion != "yaml":
                logging.error("file extension is not yaml")
            # if not exists(fullpath):
            #     logging.error(f"{fullpath} does not exist")
            else:
                break
  
        fullpath = self._base_path +f"/config/ec2/{config_file}"
        if not exists(fullpath):
            logging.error(f"{fullpath} does not exists!!")
            return 
        self._ec2_config_file = fullpath
        

        # step 2 log import file
        ec2_config_dict = convert_yaml_to_json(yaml_file=self._ec2_config_file)
        print(ec2_config_dict)
        # chcek ec2 status  
        self._login_user = ec2_config_dict['login_user']

        self._ec2_instance_id = ec2_config_dict['ec2_instance_id']
        self._keypair_name = ec2_config_dict['key_pair_name']
        if self._pem_full_path_name is None:
            self._pem_full_path_name = self._base_path + "/config/keypair"
        while True:
            pem_file_path = str(input(f"Enter the pem path (hit enter to use default path: {self._pem_full_path_name }): ") or self._pem_full_path_name )
            if not os.path.exists(pem_file_path):
                logging.debug(f"{pem_file_path} does not exist")

            else:
                break
        self._keypair_download_path = pem_file_path
        
        logging.info(f"pem file : {self._keypair_download_path}")
        full_pem =  self._keypair_download_path + f'/{self._keypair_name}.pem'
        logging.info(f"pem file and path : {full_pem}")
        self._pem_full_path_name = full_pem
        
        logging.info(f"ec2 config file :{self._ec2_config_file}")


 
        # ec2_resource = connect_aws_resource('ec2', key_id=self.aws_access_key, secret=self.aws_secret_access_key, region=self.aws_region)
        ec2_client = connect_aws_client('ec2', key_id=self.aws_access_key, secret=self.aws_secret_access_key, region=self.aws_region)
        # check ec2 status
        response = ec2_client.describe_instance_status(
            InstanceIds=[self._ec2_instance_id],
            IncludeAllInstances=True
        )
        print(f"response : {response}")
        for instance in response['InstanceStatuses']:
            instance_id = instance['InstanceId']
            if instance_id == self._ec2_instance_id:
            
                system_status = instance['SystemStatus']
                instance_status = instance['InstanceStatus']
                self._instancetState = instance['InstanceState']
                # logging.info(f"system_status :{system_status}, instance_status:{instance_status},")
        if  self._instancetState is not None:
            logging.info(f"instance state : { self._instancetState}")
        else:
            raise Exception(f"Cannot find instance state from {self._ec2_instance_id}")

    def handle_ssh_coonection(self, event):
        logging.info("Handle ssh connection")
        if self._ec2_instance_id is None or self._instancetState is None: 
            logging.error("Something wrong , no ec2 id or instance state")
            return 

        if not exists(self._pem_full_path_name):
            logging.error(f"Pem file:{self._pem_full_path_name} does not exist")
            return

        ec2_resource = connect_aws_resource('ec2', key_id=self.aws_access_key, secret=self.aws_secret_access_key, region=self.aws_region)
        try:

            res = ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).start() #for start an ec2 instance
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
        
    
    def is_confirm_creation(self):
        if self._is_confirmed == "yes":
            return True
        return False

    def set_ec2_action(self):
        inst_question =[]
        if self._ec2_action is None:
            logging.info("Set EC2 action Create, start, stop, terminate, ssh")
            inst_question = [
                inquirer.List('action',
                                message="Select action type ?",
                                choices=[EC2Action.create.name,EC2Action.start.name, EC2Action.stop.name, EC2Action.terminate.name,EC2Action.ssh.name],
                            ),
            ]
 
        else: 
            logging.info(f"Prvious ec2 action state {self._ec2_action}")
            logging.info("Set EC2 action Create, start, stop, terminate, ssh")
            inst_question = [
                inquirer.List('action',
                                message="Select action type ?",
                                choices=[EC2Action.stop.name, EC2Action.terminate.name],
                            ),
            ]

        inst_answer = inquirer.prompt(inst_question)
        self._ec2_action = inst_answer["action"]
           
        logging.info(f"Set ec2 action : {self._ec2_action}")


    def get_ec2_action(self):
        return  self._ec2_action

    def handle_ec2_action(self):
        ec2_resource = connect_aws_resource(
                resource_name='ec2',
                key_id=self.aws_access_key,
                secret=self.aws_secret_access_key,
                region=self.aws_region
        )
        if self._ec2_instance_id is None: 
            self.handle_import_configfile(self)
          

        if self._ec2_action == EC2Action.start.name:
            logging.info("Start ec2 ")
            try:
                res = ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).start() #for start an ec2 instance
                instance = check_if_ec2_ready_for_ssh(instance_id=self._ec2_instance_id, wait_time=60, delay=5, pem_location=self._pem_full_path_name,user_name=self._login_user)
            except Exception as e:
                raise Exception(f"Start ec2 failed: {e}")
            logging.info("Start instance success")
        elif self._ec2_action == EC2Action.stop.name:
            logging.info("Stop ec2")
            try:
                res = ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).stop() #for start an ec2 instance
                logging.info("Stop instance success")
            except Exception as e:
                raise Exception(f"Terminate ec2 failed: {e}")
        elif self._ec2_action == EC2Action.terminate.name:
            logging.info("Terminate ec2")
            try:
                res = ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).terminate() #for start an ec2 instance
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
    

    
    def set_security_group_info(self):
        logging.info("Set security group info")
        # security group input 
        while True:
            self._is_creating_sg = str(input(f"Create a new security group allow SSH connection only ?(default:{self._is_creating_sg}) (must be yes/no):") or self._is_creating_sg)
            if self._is_creating_sg.lower() not in ('yes', 'no'):
                print("Not an appropriate choice. please type 'yes' or 'no' !!!")
            else:
                break
    
        if self._is_creating_sg == "no":
            sg_id = input("Enter existing security group id: ")
            logging.info(f"security group id: {self._sg_ids.append(sg_id)}")
            logging.info(f"Checking security group id:{self._sg_ids}")

        else:
            print(f"Create a new security group")

       
        
    def set_keypair_info(self):
        logging.info("Set keypair info")
        while True:
            self._is_creating_keypair =  str(input(f"Create a new keypair ?(default:{self._is_creating_keypair}) (must be yes/no):") or self._is_creating_keypair)
            if self._is_creating_keypair.lower() not in ('yes', 'no'):
                print("Not an appropriate choice. please type 'yes' or 'no' !!!")
            else:
                break
         # Key pair input
        if self._is_creating_keypair == "no":
            while True:
                self._keypair_name = input("Enter existing keypair name: ")
                if len(self._keypair_name) < 2:
                    logging.error(f"Keypair name is too short: {self._keypair_name}")
                else:
                    break
            print(f"key pair name: {self._keypair_name }")
        else:
            while True:
                self._keypair_name  = input("Enter a new keypair name: ")
                if len(self._keypair_name) < 2:
                    logging.error(f"Keypair name is too short: {self._keypair_name}")
                else:
                    break
            print(f"Creating keypair: {self._keypair_name }")
        self._keypair_download_path = os.getcwd() + "/config/keypair"

        while True:
            download_path = str(input(f"Enter the pem path (hit enter to use default path: {self._keypair_download_path }): ") or self._keypair_download_path )
            if not os.path.exists(download_path):
                logging.debug(f"{download_path} does not exist")

            else:
                break
        self._keypair_download_path = download_path


       
    def set_ec2_info(self):
        logging.info("Set ec2 info")
        while True:
            self._ec2_name = input("Creat a EC2 name  :") 
            if len(self._ec2_name) < 2:
                logging.error(f"ec2 name is too short: {self._ec2_name}")
            else:
                break
        print(f"EC2 name : {self._ec2_name }")
        self._tags.append({'Key': 'Name', 'Value': self._ec2_name})
        while True:
            self._project = input("Creat a project name in tag:") 
            if len(self._project) < 2:
                logging.error(f"project name is too short: {self._project}")
            else:
                break
        print(f"Project name : {self._project }")
        self._tags.append({'Key': 'project', 'Value': self._project})
        # instance type
        inst_question = [
            inquirer.List('instance_type',
                            message="Select instance type (suggest 't2.large')?",
                            choices=['t2.large','t2.medium','t2.xlarge'],
                        ),
        ]
        inst_answer = inquirer.prompt(inst_question)
        logging.info (inst_answer["instance_type"])
        self._instancetype= inst_answer["instance_type"]

        ec2_volume = str(input(f"Enter the ec2 volume (enter for default: {self._volume}): ") or self._volume)
        self._volume = ec2_volume
        logging.info(f"Input volume: { self._volume}")
        basepath = os.getcwd()
        while True:
            export_file = str(input(f"Enter the export file name (enter for default:{self._ec2_config_file}): ") or self._ec2_config_file)
            name, extenstion = export_file.split(".")
            logging.info(f"Export file:{export_file}")
            
            if extenstion != "yaml":
                logging.error("file extension is not yaml")
            # if not exists(fullpath):
            #     logging.error(f"{fullpath} does not exist")
            else:
                break
        
        fullpath = self._base_path +f"/config/ec2/{export_file}"
        self._ec2_config_file = fullpath
        
        print(f"self._ec2_config_file :{self._ec2_config_file}")

        # running, stopped,or terminate after completion.
        action_questions = [
            inquirer.List('action',
                            message="Select an action after process completed ?",
                            choices=[EC2Action.running.name,EC2Action.stop.name, EC2Action.terminate.name],
                        ),
        ]
        inst_answer = inquirer.prompt(action_questions)
        
        self._ec2_action = inst_answer["action"]
        if self._ec2_action == EC2Action.terminate.name:
            while True:
                self._is_remove_all_created_resources = str(input(f"Is removeall created resource after terminate ec2? {self._is_remove_all_created_resources }): ") or self._is_remove_all_created_resources )
                if self._is_remove_all_created_resources.lower() not in ('yes', 'no'):
                    print("Not an appropriate choice. please type 'yes' or 'no' !!!")
                else:
                    break
            print(f"Remove all created resources : {self._is_remove_all_created_resources}")
            

    def set_eks_cluster_info(self):
        logging.info("Set eks cluster info")
        # create eks cluster
        while True:
            self._is_creating_eks =  str(input(f"Create a new eks cluster ?(default:{self._is_creating_eks}) (must be yes/no):") or self._is_creating_eks)
            if self._is_creating_eks.lower() not in ('yes', 'no'):
                print("Not an appropriate choice. please type 'yes' or 'no' !!!")
            else:
                break

        # import clustr config
        if  self._is_creating_eks == "yes":
            while True:
                eks_configfile = str(input(f"Enter the eks cluster file name (default:{self._eks_configfile}): ") or self._eks_configfile)
                name, extension = eks_configfile.split(".")
                logging.info(f"Create eks cluster from file:{eks_configfile}")
                if extension != "yaml":
                    logging.error(f"{name}.{extension} is not a yaml file!!")
               
                eksfullpath = self._base_path +f"/config/eks/{eks_configfile}"
                if not os.path.exists(eksfullpath):
                    logging.error(f"{eksfullpath} does not exist. Please try again!! (under path: {self._base_path}/config/eks/ )")
                else:
                    break
            self._eks_configfile = eksfullpath
            # delete cluter at end 
            while True:
                self._delete_eks_cluster = str(input(f"Delete EKS after completion?(default:{self._delete_eks_cluster}) (must be yes/no):") or self._delete_eks_cluster)
                if self._delete_eks_cluster.lower() not in ('yes', 'no'):
                    print("Not an appropriate choice. please type 'yes' or 'no' !!!")
                else:
                    break

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
        ec2_client = connect_aws_client(
            client_name= 'ec2',
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region
        )
        # VPC ID 
        if self._use_deafualt_vpc == "yes":
                logging.info("Use default vpc")
                self._vpc_id = get_default_vpc_id(ec2_client=ec2_client)
        else:     
            logging.info(f"Checking VPC : {self._vpc_id}")
            if not check_vpc_id_exists(ec2_client=ec2_client, vpc_id= self._vpc_id):
                logging.error(f"Cannot find vpc id {self._vpc_id}")
                return 


        # Check security group 
        if self._is_creating_sg == "yes":
            logging.info(f"Checking security group  : {self._sg_ids}")
            sg_id = check_sg_group_name_exists_and_return_sg_id(
                ec2_client= ec2_client,
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
                ec2_client=ec2_client,
                keypair_name=self._keypair_name):
                logging.error(f"Cannot find keypair: {self._keypair_name}")
                return 
        
        
        cloud_resource = [
			["Parameters","Details"],
			["Use default VPC", self._use_deafualt_vpc, self._vpc_id ],
			["Create security group",self._is_creating_sg, self._sg_ids],
			["Create a new keypair",self._is_creating_keypair, self._keypair_name],
            ["Keypair download path",self._keypair_download_path],
            ["Image id",self._image_id],
            ["Instance type",self._instancetype],
            ["volume",self._volume],
            ["tags",self._tags],
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


    
    def hanlde_create_cloud_resources(self, event):
        logging.info("Handle create resources")
        ec2_client = connect_aws_client(
            client_name="ec2",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        # Create security group
        if self._is_creating_sg == "yes":
            logging.info("Create security group")
            try:
                security_info_dict = create_security_group(
                    ec2_client=ec2_client,
                    vpc_id=self._vpc_id,
                    tags=self._tags,
                    group_name=self._sg_name
                )
            except Exception as e:
                logging.error(f"Create Security group failed :{e}")
                raise e
            self._sg_id = security_info_dict['security_group_id']
            self._vpc_id = security_info_dict['vpc_id']
            print(f"Create SecurityGroupIds : {self._sg_id} in vpc_id:{self._vpc_id} success")

        # Create Key pair
        if self._is_creating_keypair == "yes":
            try:
                create_key_pair(ec2_client=ec2_client, keyname=self._keypair_name, file_location=self._keypair_download_path)
            except Exception as e:
                logging.error(f"Create key pair error :{e}")
                raise e
        return 

    def handle_create_ec2(self, event):
        logging.info("Handle create ec2")
        ec2_client = connect_aws_client(
            client_name="ec2",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        try:
            ec2_instance_id = create_instance(     
                ImageId=self._image_id,
                InstanceType = self._instancetype,
                key_piar_name = self._keypair_name,
                ec2_client=ec2_client,
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

        logging.info("-------------------")
        logging.info(f"Export ec2 bastion setting to {self._ec2_config_file}")
        logging.info("-------------------")

       
    

    def handle_install_dependencies(self, event):
        logging.info("Handle install dependencies")
        pem_file=self._keypair_download_path +"/"+self._keypair_name+".pem"
        instance = check_if_ec2_ready_for_ssh(
            instance_id=self._ec2_instance_id , 
            wait_time=self._ssh_total_wait_time, 
            delay=self._ssh_wait_time_interval, 
            pem_location=pem_file,
            user_name=self._login_user)

        logging.info(f"instance ready :{instance}")

        ec2_client = connect_aws_client(
            client_name="ec2",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        self._ec2_public_ip = get_public_ip(
            ec2_client=ec2_client,
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
            ec2_client=ec2_client,
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
            ec2_client=ec2_client
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
            ec2_client=ec2_client,
            local_file=local_env,
            remote_file=remote_env,
        )
        logging.info("-------------------")
        logging.info(f"upload config folder")
        logging.info("-------------------")

        ssh_upload_folder_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=pem_file,
            local_folder= self._base_path + "/config",
            remote_folder=f"{remote_base_path}/config",
            ec2_client=ec2_client,

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
        # remote_file=f"{remote_base_path}/config/k8s/{file}"
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


        write_aws_setting_to_yaml(
            file=self._ec2_config_file, 
            setting=ec2_json
        )


    def set_eks_action(self):
        logging.info("Set EKS action")
        inst_question = [
            inquirer.List('action',
                            message="Select eks action type ?",
                            choices=[EKSAction.create.name,EKSAction.delete.name, EKSAction.list.name, EKSAction.scaledownzero.name],
                        ),
        ]
        inst_answer = inquirer.prompt(inst_question)

        self._eks_action = inst_answer["action"]

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
    
        ec2_client = connect_aws_client('ec2', key_id=self.aws_access_key, secret=self.aws_secret_access_key, region=self.aws_region)
        ssh_upload_folder_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_full_path_name,
            local_folder= "./config",
            remote_folder=f"{remote_base_path}",
            ec2_client=ec2_client,

        )
        logging.info("update config folder completed")
    #
    def set_and_run_ssh_command(self):
        logging.info("set and run  ssh command")
        self._ssh_command = input(f"Please type your command: ")
        logging.info(f"command : {self._ssh_command}")
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
        ssh_command = f"cd {remote_base_path} \n source ./venv/bin/activate\n export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env )  \n{self._ssh_command} "
        ec2_client = connect_aws_client('ec2', key_id=self.aws_access_key, secret=self.aws_secret_access_key, region=self.aws_region)
        run_command_in_ec2_ssh(
            user_name= self._login_user,
            instance_id= self._ec2_instance_id,
            pem_location=self._pem_full_path_name,
            ec2_client=ec2_client,
            command=ssh_command
        )

        
    def get_ssh_command(self):
        return  self._ssh_command

    def import_ec2_info_from_config(self, config_file:str):
        self._ec2_config_file = config_file
        ec2_json = convert_yaml_to_json(yaml_file= self._ec2_config_file)
        
        self._keypair_name = ec2_json['key_pair_name']
        self._tags = ec2_json['tags']
        self._keypair_download_path = ec2_json['pem_location']
        self._ec2_instance_id = ec2_json['ec2_instance_id']
        pem_file=self._keypair_download_path  +"/"+self._keypair_name+".pem"
        self._login_user = ec2_json['user_name']

        # check instance id status
        
    


    
    def start_ec2(self):
        ec2_resource = connect_aws_resource(
            resource_name='ec2',
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region
        )
        ec2_client = connect_aws_client(
            client_name="ec2",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        pem_file=self._keypair_download_path  +"/"+self._keypair_name+".pem"
        if self._ec2_instance_id is not None:
            res = ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).start() #for stopping an ec2 instance
            instance = check_if_ec2_ready_for_ssh(instance_id=self._ec2_instance_id, wait_time=self._ssh_total_wait_time, delay=self._ssh_wait_time_interval, pem_location=pem_file,user_name=self._login_user)
            self._ec2_public_ip = get_public_ip(
                ec2_client=ec2_client,
                instance_id=self._ec2_instance_id
            )
            logging.info("---------------------")
            logging.info(f"public_ip :{self._ec2_public_ip}")
            logging.info("---------------------")

        else:
            logging.error("ec2_resource id is None")
            return
    
    def stop_ec2(self):
        ec2_resource = connect_aws_resource(
            resource_name='ec2',
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region
        )
        if self._ec2_instance_id is not None:
            res = ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).stop() #for stopping an ec2 instance
            logging.info(f"Stop {self._ec2_instance_id} success")
            return
        else:
            logging.error("ec2_resource id is empty")
            return
    def terminate_ec2(self):
        
        logging.info("terminate ec2")
        ec2_resource = connect_aws_resource(
            resource_name='ec2',
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region
        )
        if self._ec2_instance_id is not None:
            res = ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).stop() #for stopping an ec2 instance
            res_term  = ec2_resource.instances.filter(InstanceIds = [self._ec2_instance_id]).terminate() #for terminate an ec2 insta
        else:
            logging.error("ec2_resource id is empty")
            return


    def handle_eks_action(self, event):
        logging.info("Handle create eks cluster")
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/gismoclouddeploy/services"
        path, file  = os.path.split(self._eks_configfile)
        remote_cluster_file=f"{remote_base_path}/config/eks/{file}"
        
        command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl create cluster -f {remote_cluster_file}"
        ec2_client = connect_aws_client(
            client_name="ec2",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        if self._eks_action == EKSAction.create.name:
            logging.info("Create cluster through SSH from local")
            command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl create cluster -f {remote_cluster_file}"
            
        elif self._eks_action == EKSAction.delete.name:
            logging.info("Delete cluster throuth SSH from local")
            command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl delete cluster -f {remote_cluster_file}"

        elif self._eks_action == EKSAction.list.name:
            logging.info("List all eks cluster")
            command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl get cluster"

        elif self._eks_action == EKSAction.scaledownzero.name:
            logging.info("Scale to zero")
            cluster_dict = convert_yaml_to_json(yaml_file=self._eks_configfile)
            cluster_name = cluster_dict['metadata']['name']
            if len (cluster_dict['nodeGroups']) == 0 :
                logging.error("nodeGroup does not defined")
                return 
            group_name = cluster_dict['nodeGroups'][0]['name']
            command = f"export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n eksctl scale nodegroup --cluster {cluster_name} --name {group_name} --nodes 0"
        else:
            logging.error(f"unknow action: {self._eks_action} ")
            return 


        pem_file=self._keypair_download_path +"/"+self._keypair_name+".pem"
        run_command_in_ec2_ssh(
                    user_name=self._login_user,
                    instance_id=self._ec2_instance_id,
                    command=command,
                    pem_location=pem_file,
                    ec2_client=ec2_client
             )
        

    def handle_export_to_file(self, event):
        logging.info("Handle create eks cluster")

    def handle_cleanup(self, event):
        logging.info("Handle clean up")




def get_default_vpc_id(ec2_client) -> str:
    logging.info("get default VPC id ")
    try:
        response = ec2_client.describe_vpcs()
        if len(response) > 0 :
            vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
            return vpc_id
        else:
            return None
    except Exception as e:
        raise Exception(f"Get default vpc id failed")

def check_vpc_id_exists(ec2_client,vpc_id:str) -> bool:
    try:
        response = ec2_client.describe_vpcs(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        resp = response['Vpcs']
        if resp:
            return True
    except Exception as e:
        logging.error("FInd VPC id error")
    return False

def check_sg_group_name_exists_and_return_sg_id(ec2_client , group_name:str) -> str:
    logging.info("Check security group id ")
    try:
        response = ec2_client.describe_security_groups(
            GroupNames=[group_name],
        )
       
        if len(response['SecurityGroups']) > 0 :
             return (response['SecurityGroups'][0]['GroupId'])

    except Exception as e:
        logging.error(f"FInd security group error :{e}")
    return None



def check_keypair_name_exists(ec2_client ,keypair_name:str) -> bool:
    logging.info("Check key pairname ")
    try:
        response = ec2_client.describe_key_pairs(
            KeyNames=[keypair_name]
        )
        if len(response)> 0:
            logging.info(f" {keypair_name} exists")
            return True
    except Exception as e:
        logging.error(f"{keypair_name} does not exist")
        return False

