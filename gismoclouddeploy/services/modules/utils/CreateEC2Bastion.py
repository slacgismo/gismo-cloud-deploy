
from transitions import Machine
import os
import coloredlogs, logging
from terminaltables import AsciiTable
import inquirer
from .EC2Action import EC2Action

from .check_aws import (
    connect_aws_client,
    check_environment_is_aws,
    connect_aws_resource,
)
from .create_ec2 import create_security_group
from .EC2Action import EC2Action
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
        self._sg_id = None
        self._keypair_name = None
        self._keypair_dwon_path = None
        self._image_id = "ami-0568773882d492fc8"
        self._instancetype= "t2.large"
        self._volume = 16
        self._ec2_name = None
        self._export_file = 'config-ec2.yaml'
        self._project = None
        self._tags = [
            {'Key': 'managedBy', 'Value': 'boto3'}
        ]
        self._run_process_files = "yes"
        self._delete_eks_cluster = "yes"
        self._ec2_action = EC2Action.stop.name

        self._is_remove_all_created_resources = "no"


        self._is_confirmed = "no"
        self._is_process_default_files = "no"
        self._process_first_n_files = 1

        self._config_file = "config.yaml"
        self._ssh_command = ""

        
        
        self.machine = Machine(model=self, states=CreateEC2Bastion.states, initial='system_stop', on_exception='handle_error',send_event=True)
        # create ec2 steps 
        self.machine.add_transition(trigger='trigger_initial', source='system_stop', dest='system_initial', after='handle_verify_input')
        self.machine.add_transition(trigger='trigger_resources_ready', source='system_initial', dest='cloud_resources_ready', after ='hanlde_create_cloud_resources')
        self.machine.add_transition(trigger='trigger_create_ec2', source='cloud_resources_ready', dest='ec2_ready', before ='handle_create_ec2', after="handle_install_dependencies")
        self.machine.add_transition(trigger='trigger_create_eks', source='ec2_ready', dest='eks_ready', before ='handle_create_eks_cluster')
        self.machine.add_transition(trigger='trigger_cleanup', source='*', dest='cleanup', before ='handle_cleanup', after = 'handle_export_to_file')

        # ssh steps  (create_eks, delete_eks, run-files)

        self.machine.add_transition(trigger='trigger_ssh', source='system_stop', dest='ec2_ready',before='hand_import_files_and_verify_inputs' ,after='handle_ssh_coonection')
 


        
    def handle_error(self, event):
        raise ValueError(f"Oh no {event.error}") 
    
    def is_confirm_creation(self):
        if self._is_confirmed == "yes":
            return True
        return False

    def set_ec2_action(self):
        logging.info("Set EC2 action")
        inst_question = [
            inquirer.List('action',
                            message="Select action type ?",
                            choices=[EC2Action.create.name,EC2Action.start.name, EC2Action.stop.name, EC2Action.terminate.name,EC2Action.ssh.name],
                        ),
        ]
        inst_answer = inquirer.prompt(inst_question)

        self._ec2_action = inst_answer["action"]

    def get_ec2_action(self):
        return  self._ec2_action

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
            self._sg_id = input("Enter existing security group id: ")
            logging.info(f"security group id: {self._sg_id}")
            logging.info(f"Checking security group id:{self._sg_id}")

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
            self._keypair_dwon_path = os.getcwd() + "/config/keypair"

            while True:
                download_path = str(input(f"Enter the download path (hit enter to use default file: {self._keypair_dwon_path }): ") or self._keypair_dwon_path )
                if not os.path.exists(download_path):
                    logging.debug(f"{download_path} does not exist")

                else:
                    break
            self._keypair_dwon_path = download_path


       
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
        while True:
            export_file = str(input(f"Enter the export file name (enter for default:{self._export_file}): ") or self._export_file)
            name, extenstion = export_file.split(".")
            logging.info(f"Export file:{export_file}")
            if extenstion != "yaml":
                logging.debug("file extension is not yaml")

            else:
                break
        self._export_file = export_file
        print(f"self._export_file :{self._export_file}")

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
                basepath = os.getcwd()
                eksfullpath = basepath +f"/config/eks/{eks_configfile}"
                if not os.path.exists(eksfullpath):
                    logging.error(f"{eksfullpath} does not exist. Please try again!! (under path: {basepath}/config/eks/ )")
                else:
                    break
            self._eks_configfile = eks_configfile
            # delete cluter at end 
            while True:
                self._delete_eks_cluster = str(input("Delete EKS after completion? (must be yes/no):") or self._delete_eks_cluster)
                if self._delete_eks_cluster.lower() not in ('yes', 'no'):
                    print("Not an appropriate choice. please type 'yes' or 'no' !!!")
                else:
                    break

    def set_runfiles_command(self):
        logging.info("Set runfile command after eks cluster ready")
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
        if self._vpc_id is not None:
            logging.info(f"Checking VPC : {self._vpc_id}")
            check_vpc_id_exists(vpc_id=self._vpc_id)
        if self._sg_id is not  None:
            logging.info(f"Checking security group  : {self._sg_id}")
            check_sg_id_exists(sg_id=self._sg_id)
        if self._keypair_name is not None:
            logging.info(f"Checking key pair  : {self._keypair_name}")
            check_keypair_name_exists(keypair_name=self._keypair_name)
        
        cloud_resource = [
			["Parameters","Details"],
			["Use default VPC", self._use_deafualt_vpc, self._vpc_id ],
			["Create security group",self._is_creating_sg, self._sg_id],
			["Create a new keypair",self._is_creating_keypair, self._keypair_name],
            ["Keypair download path",self._keypair_dwon_path],
            ["Image id",self._image_id],
            ["Instance type",self._instancetype],
            ["volume",self._volume],
            ["tags",self._tags],
            ['EKS cluster file', self._eks_configfile],
            ['Config file', self._config_file],
            ["Export file name",self._export_file],
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

        if self._is_creating_sg:
            logging.info("Create security group")
            try:
                security_info_dict = create_security_group(
                    ec2_client=ec2_client,
                    vpc_id=self._vpc_id,
                    tags=self._tags
                )
            except Exception as e:
                logging.info(f"Create Security group failed :{e}")
                raise e
            self._sg_id = security_info_dict['security_group_id']
            self._vpc_id = security_info_dict['vpc_id']
            print(f"Create SecurityGroupIds : {self._sg_id} in vpc_id:{self._vpc_id} success")
        

    def handle_create_ec2(self, event):
        logging.info("Handle create ec2")

    def handle_install_dependencies(self, event):
        logging.info("Handle install dependencies")


    def handle_create_eks_cluster(self, event):
        logging.info("Handle create eks cluster")
    
    def handle_export_to_file(self, event):
        logging.info("Handle create eks cluster")

    def handle_cleanup(self, event):
        logging.info("Handle clean up")


def check_vpc_id_exists(vpc_id:str) -> bool:
    logging.info("Check VPC id ")

def check_sg_id_exists(sg_id:str) -> bool:
    logging.info("Check security group id ")

def check_keypair_name_exists(keypair_name:str) -> bool:
    logging.info("Check key pairname ")

