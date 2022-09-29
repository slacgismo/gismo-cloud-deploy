
from random import randrange
from sre_parse import FLAGS
import time
import os
from os.path import  basename, exists
import logging
import inquirer
import shutil
from terminaltables import AsciiTable
from mainmenu.classes.constants.AWSActions import AWSActions
from mainmenu.classes.constants.InputDescriptions import InputDescriptions
from .constants.MenuActions import MenuActions
from .constants.EKSActions import EKSActions
from .constants.EC2Actions import EC2Actions
from .utilities.convert_yaml import convert_yaml_to_json,write_aws_setting_to_yaml
from .utilities.verification import (
    verify_keys_in_ec2_configfile,
    verify_keys_in_eks_configfile,
    verify_keys_in_configfile,
)
import difflib
import sys
sys.path.append('../../gismoclouddeploy')
from gismoclouddeploy.gismoclouddeploy import gismoclouddeploy
from .AWSServices import AWSServices

# setting path
# # sys.path.append('../../gismoclouddeploy/gismoclouddeploy.py')
# from gismoclouddeploy import gismoclouddeploy

from .utilities.handle_inputs import(
    handle_input_project_path_question,
    hanlde_input_project_name_in_tag,
    handle_yes_or_no_question,
    handle_input_number_of_process_files_question,
    handle_input_number_of_scale_instances_question,
    select_acions_menu,
    enter_the_working_project_path
)
from transitions import Machine
from .utilities.aws_utitlties import (
    connect_aws_client,
    get_iam_user_name
)


class FiniteStateMachineOld(object):
    states=[
            'start',
            'init', 
            'creation',
            'wakeup',
            'process',
            'end',
        ]


    default_answer = {
        "default_project": "examples/sleep",
        "project_in_tags" : "pvinsight",
        "is_ssh": "no",
        "num_of_nodes":1,
        "cleanup_resources_after_completion" : "no",
        "is_process_all_file":"no",
        "process_first_n_files":1,
        "num_of_nodes":1,
        "max_node":100
    }

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
        self.ec2_config_templates = ec2_config_templates
        self.eks_config_templates = eks_config_templates
        self.local_pem_path = local_pem_path 


        self._action = None
        self._origin_project_path = None
        self._base_path = os.getcwd()
        self._project_name = None
        self._select_history_path = None
        # self._run_files_command = None

        # self._user_id = self._set_user_id()
        self._system_id = None
        self._start_time = str(int(time.time()))

        self._ec2_config_dict = {}
        self._eks_config_dict = {}

        self._input_answers = {}
        self._aws_services = None


        self.machine = Machine(model=self, states=FiniteStateMachine.states, initial='start', on_exception='handle_error',send_event=True)

        self.machine.add_transition(trigger='trigger_initial', source='start', dest='init', before="hanlde_init",after="handle_confirmation")
        self.machine.add_transition(trigger='trigger_creation', source='init', dest='creation', before="handle_create_ec2", after="handle_create_eks")
        self.machine.add_transition(trigger='trigger_wakeup', source='creation', dest='wakeup', before="handle_verify_system",after="handle_wakeup")
        self.machine.add_transition(trigger='trigger_process', source='wakeup', dest='process', after="handle_cloud_processing")
        # clean up resouces


        # run in local machine
        self.machine.add_transition(trigger='trigger_run_local', source='init', dest='process', after="handle_local_processing")
        
        # End of application
        self.machine.add_transition(trigger='trigger_end', source='*', dest='end', before ='handle_cleanup_cloud_resources', after = 'handle_completion')

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

    def _generate_system_id(self):
        user_id = self._set_user_id()
        return  f"gcd-{user_id}-{self._start_time}"
    # def _generate_ec2_name(self):
    #     return f"gcd-{self._user_id}-{self._start_time}"
    # def _generate_eks_cluster_name(self):
    #     return f"gcd-{self._user_id}-{self._start_time}"
    def _generate_keypair_name(self):
        return f"gcd-{self._user_id}"

    def get_action(self):
        return self._action

    def handle_error(self, event):
        raise ValueError(f"Error: {event.error}") 



    # Initial state 

    def hanlde_init(self,event):
        logging.info("actions selection")


        self._action = select_acions_menu()
        self._origin_project_path = enter_the_working_project_path(default_project=FiniteStateMachine.default_answer['default_project'])
        self.set_project_name()
        self.copy_origin_project_into_temp_folder()

        # step 1 . ask for project
        self._input_answers = handle_proecess_files_inputs_questions(action=self._action, default_answer=FiniteStateMachine.default_answer)

        # hande import ec2 eks cloud resources
        if self._action == MenuActions.resume_from_existing.name \
            or self._action == MenuActions.cleanup_cloud_resources.name:

            logging.info("Import history cloud resources config")
            self._select_history_path  = select_created_cloud_config_files(saved_config_path_base=self.saved_config_path_base)
            logging.info(f"Select history path : {self._select_history_path}")
            ec2_config_file = self._select_history_path +"/config-ec2.yaml"
            print(f"ec2_config_file :{ec2_config_file}")
            try:
                self._ec2_config_dict = import_and_verify_ec2_config(ec2_config_file=ec2_config_file)
                tags = self._ec2_config_dict['tags']
                for tag in tags:
                    print(tag)
                    if 'Key' in tag and 'Value' in tag and tag['Key'] == "Name" :
                            self._system_id = tag['Value']
                if self._system_id is None:
                    raise Exception("No ec2 name in tags , syste id is None")

            except Exception as e:

                raise Exception(f"Import and verify history ec2 file failed: {e}")
            eks_config_file = self._select_history_path +"/cluster.yaml"
            try:
                self._eks_config_dict = import_from_eks_config(saved_eks_config_file = eks_config_file)
            except Exception as e:
                logging.warning("A EC2 file exists but a eks file does not exists")
                logging.warning("It still goes to next state to check if the ec2 exists. ")
                logging.warning("If the ec2 exists and no eks cluster had been created, it creates a new cluster.")
                logging.warning("If the ec2 does not exist, raies exception and delete this hitory file")
                raise Exception("Terminates up ec2 and ask to re create a new cluster again")
                # raise Exception("selected EKS config history file does not exist")

        elif self._action == MenuActions.create_cloud_resources_and_start.name:
            logging.info("Generate ec2_dict from template")
            print(f"self.ec2_config_templates: {self.ec2_config_templates}")
            try:
                # import template
                self._ec2_config_dict = import_and_verify_ec2_config(ec2_config_file=self.ec2_config_templates)
                self._eks_config_dict = import_from_eks_config(saved_eks_config_file = self.eks_config_templates)
                # generate parameters and replace template dict
                # generate ec2 and eks cluster name 
                if self._user_id is None or self._start_time is None:
                    raise Exception("user id or start time is None")

                project_in_tags = self._input_answers['project_in_tags']

                self._system_id =  self._generate_system_id()



                cluster_name = self._system_id
                keypair_name = self._generate_keypair_name()

                # replace ec2 config 
                self._ec2_config_dict['key_pair_name'] = keypair_name
                ec2_project_tags = {"Key":"project", "Value": project_in_tags}
                ec2_name_tags = {"Key":"Name", "Value": self._system_id}
                # append tags
                self._ec2_config_dict['tags'].append(ec2_project_tags)
                self._ec2_config_dict['tags'].append(ec2_name_tags)

                
                # replace eks config
                self._eks_config_dict['metadata']['name'] = cluster_name
                self._eks_config_dict['metadata']['region'] = self.aws_region
                self._eks_config_dict['metadata']['tags']['project'] = project_in_tags
                self._eks_config_dict['nodeGroups'][0]['tags']['project'] = project_in_tags
                logging.info("Generate ec2, eks parameters from templates success")
                print(self._eks_config_dict)
                return 
            except Exception as e:
                raise Exception(f"Generate ec2, eks parameters from templates failed :{e}")

    
    # Creation state
    def handle_confirmation(self,event):
        logging.info("handle verification")

        # print out ec2, eks parameters
        if self._action == MenuActions.cleanup_cloud_resources.name or \
            self._action == MenuActions.resume_from_existing.name or \
                self._action == MenuActions.create_cloud_resources_and_start.name:
            
            logging.info("Print out ec2, eks variables")
            ec2_arrays = [["EC2 setting", "Details"]]
            # EC2 table
            for key, value in self._ec2_config_dict.items():
                    array = [key, value]
                    ec2_arrays.append(array)
            ec2_table = AsciiTable(ec2_arrays)
            print(ec2_table.table)
            # EKS table
            cluster_name = None
            if len(self._eks_config_dict) and 'metadata' in self._eks_config_dict:
                cluster_name = self._eks_config_dict['metadata']['name']
            
            if cluster_name is None:
                logging.warning("No eks cluster informations")
                logging.warning("If confirm to process, it will generate a new cluster, with a new name")
            
            else:
                eks_arrays = [["EKS cluster name", cluster_name]]
                for key, value in self._eks_config_dict.items():
                        array = [key, value]
                        eks_arrays.append(array)
                eks_table = AsciiTable(eks_arrays)
                print(eks_table.table)

        

        # create run-command 
        # is_ssh = self._input_answers['is_ssh']


        if self._action == MenuActions.resume_from_existing.name or \
                self._action == MenuActions.create_cloud_resources_and_start.name or \
                    self._action == MenuActions.run_in_local_machine.name:
            input_arrays = [["Input parameters", "answer"]]
            logging.info("Print out input questions answer")
            for key, value in self._input_answers.items():
                    array = [key, value]
                    input_arrays.append(array)
            # input_arrays.append(["run_files command",self._run_files_command])
            input_table = AsciiTable(input_arrays)
            
            print(input_table.table)


    def handle_export(self, event):
        logging.info("handle_export")



    def is_confirm_to_process(self) -> bool:
        is_comfirm = handle_yes_or_no_question(
            input_question="Confirm to process (must be yes/no)",
            default_answer="yes"
        )

        return is_comfirm

    
    def handle_create_ec2(self,event):
        logging.info("handle create cloud resources")
        if self._action == MenuActions.run_in_local_machine.name or \
            self._action == MenuActions.cleanup_cloud_resources.name:
            raise Exception(f"Action: {self._action} should not trigger this state. Please check your code")
        # init aws services 
 
        temp_project_absoult_path = get_absolute_paht_from_project_name(project_name=self._project_name, base_path=self._base_path)
        keypair_name = self._ec2_config_dict['key_pair_name']
        ec2_tags = self._ec2_config_dict['tags']
        ec2_image_id = self._ec2_config_dict['ec2_image_id']
        ec2_instance_type = self._ec2_config_dict['ec2_instance_type']
        ec2_volume = self._ec2_config_dict['ec2_volume']
        login_user = self._ec2_config_dict['login_user']
        securitygroup_name = self._ec2_config_dict['securitygroup_name']
        
        logging.info("Init aws services")
        self._aws_services = AWSServices(
                keypair_name = keypair_name,
                local_pem_path=self.local_pem_path,
                aws_access_key=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_region= self.aws_region,
                saved_config_path_base = self.saved_config_path_base,
                ec2_tags = ec2_tags,
                local_temp_project_path = temp_project_absoult_path,
                project_name = self._project_name,
                origin_project_path=self._origin_project_path,
            )

        if self._action == MenuActions.create_cloud_resources_and_start.name:
            logging.info("Start to create cloud resource")
            self._aws_services.create_ec2_from_template_file(
                ec2_image_id=ec2_image_id,
                ec2_instance_type=ec2_instance_type,
                ec2_volume=ec2_volume,
                login_user=login_user,
                securitygroup_name=securitygroup_name
            )
            
                    # step 4 , generate history path and export ec2 setting
            ec2_name = self._generate_ec2_name()
            self._aws_services.generate_config_history_path(id=ec2_name)
            export_ec2_file = self.saved_config_path_base + f"/{ec2_name}/config-ec2.yaml"
            self._aws_services.export_ec2_params_to_file(
                export_file=export_ec2_file
            )
            # step 5 , install dependencies
            self._aws_services.hanle_ec2_setup_dependencies()

    def handle_create_eks(self, event):
        logging.info("handle create eks")
        if self._action == MenuActions.run_in_local_machine.name or \
            self._action == MenuActions.cleanup_cloud_resources.name:
            raise Exception(f"Action: {self._action} should not trigger this state. Please check your code")
        if self._aws_services is None :
            raise Exception("AWS services is None")

        if self._action == MenuActions.create_cloud_resources_and_start.name:
            try:
                ec2_config_file = self.saved_config_path_base +f"/{self._system_id}/config-ec2.yaml"
                if not exists(ec2_config_file):
                    raise Exception(f"{ec2_config_file} does not exist")
                ec2_dict = convert_yaml_to_json(yaml_file=ec2_config_file)
                ec2_instance_id = ec2_dict['ec2_instance_id']
                login_user = ec2_dict['login_user']
                key_pair_name = ec2_dict['key_pair_name']

            except Exception as e:
                raise Exception(f"Parse ec2 config file failed: {e}")

            try:
                self._aws_services.generate_eks_config_and_export(eks_config_yaml_dcit=self._eks_config_dict)
                # upload local cluster file to cloud 
                self._aws_services.ssh_update_eks_cluster_file()
                # create eks cluster
                cluster_name = self._eks_config_dict['metadata']['name']
                nodegroup_name = self._eks_config_dict['nodeGroups'][0]['name']
                remote_base_path = f"/home/{login_user}/gismo-cloud-deploy"
                remote_cluster_file =f"{remote_base_path}/created_resources_history/{self._system_id}/cluster.yaml"
                self._aws_services.handle_ssh_eks_action(
                    eks_action=EKSActions.create.name,
                    cluster_name=cluster_name,
                    nodegroup_name=nodegroup_name,
                    login_user=login_user,
                    instance_id=ec2_instance_id,
                    remote_cluster_file=remote_cluster_file
                )
            except Exception as e:
                raise Exception(f"Create EKS cluster failed :{e}")
        
        logging.info("Inatallization completed")

    def handle_verify_system(self, event):
        logging.info("Check cloud resources")
        # check keypair 
        try:
            self._aws_services.handle_aws_actions(action=AWSActions.create_keypair.name)
        except Exception as e:
            raise Exception(f"check keypair error:{e}")
        # check ec2 status
        try:
            ec2_config_file = self.saved_config_path_base +f"/{self._system_id}/config-ec2.yaml"
            if not exists(ec2_config_file):
                raise Exception(f"{ec2_config_file} does not exist")
            ec2_dict = convert_yaml_to_json(yaml_file=ec2_config_file)
            ec2_instance_id = ec2_dict['ec2_instance_id']
            login_user = ec2_dict['login_user']
            key_pair_name = ec2_dict['key_pair_name']
            if ec2_instance_id is None:
                raise Exception("ec2 instance id is None")
            self._aws_services.wake_up_ec2(
                ec2_instance_id=ec2_instance_id,
                login_user=login_user,
                key_pair_name=key_pair_name
            )
        except Exception as e:
            raise Exception(f"Wakeup ec2 failed :{e}")
        # check eks cluster exist
        logging.info("Check if eks cluster exist")
        eks_config_file = self.saved_config_path_base +f"/{self._system_id}/cluster.yaml"
        if not exists(eks_config_file):
            raise Exception(f"{eks_config_file} does not exist")
        eks_dict = convert_yaml_to_json(yaml_file=eks_config_file)
        cluster_name = eks_dict['metadata']['name']
        nodegroup_name = eks_dict['nodeGroups'][0]['name']
        if ec2_instance_id is None:
            raise Exception("ec2_instance_id is None")
        print(f"ec2_instance_id :{ec2_instance_id}")


        try:
            find_cluster_name = self._aws_services.check_eks_exist(
                cluster_name=cluster_name,
                instance_id=ec2_instance_id,
                login_user=login_user
            )
            find_cluster_name = find_cluster_name.strip('\n').strip('\r')
            print(str(find_cluster_name))
            if str(find_cluster_name) == str(cluster_name):
                logging.info(f"{find_cluster_name} found and match to savd eks cluster.yaml")
            else:
                output_list = [li for li in difflib.ndiff(find_cluster_name, cluster_name) if li[0] != ' ']
                logging.error(f"two string cluster different: {output_list}")
                raise Exception(f"{find_cluster_name} does not exsit on AWS ")

        except Exception as e:
            raise Exception(f"list eks cluster failed :{e}")

    # Wakeup  state
    def handle_import_configfiles(self,event):
        logging.info("handle import configfile")
        
    def handle_wakeup(self,event):
        logging.info("handle wakeup")
        # try ssh connection


    # process state

    
    # End state
    def handle_cleanup_cloud_resources(self,event):
        logging.info("handle clean up ")
        is_cleanup_resources_after_completion = False

        if self._input_answers is not None:
            if "cleanup_resources_after_completion" in self._input_answers:
                is_cleanup_resources_after_completion = self._input_answers['cleanup_resources_after_completion']
        try:
            ec2_config_file = self.saved_config_path_base +f"/{self._system_id}/config-ec2.yaml"
            if not exists(ec2_config_file):
                raise Exception(f"{ec2_config_file} does not exist")
            ec2_dict = convert_yaml_to_json(yaml_file=ec2_config_file)
            ec2_instance_id = ec2_dict['ec2_instance_id']
            login_user = ec2_dict['login_user']
            key_pair_name = ec2_dict['key_pair_name']
        except Exception as e:
            raise Exception ("Parse ec2 from file failed")

        try:
            eks_config_file = self.saved_config_path_base +f"/{self._system_id}/cluster.yaml"
            if not exists(eks_config_file):
                raise Exception(f"{eks_config_file} does not exist")
            eks_dict = convert_yaml_to_json(yaml_file=eks_config_file)
            cluster_name = eks_dict['metadata']['name']
            nodegroup_name = eks_dict['nodeGroups'][0]['name']
            remote_base_path = f"/home/{login_user}/gismo-cloud-deploy"
            remote_cluster_file =f"{remote_base_path}/created_resources_history/{self._system_id}/cluster.yaml"
        except Exception as e:
            raise Exception("Parse eks file failed")

        if self._action == MenuActions.cleanup_cloud_resources.name or \
            is_cleanup_resources_after_completion is True:
            logging.info("Clean up cloud resources")
            # delete eks cluster
            try:
                self._aws_services.handle_ssh_eks_action(
                    eks_action=EKSActions.delete.name,
                    cluster_name=cluster_name,
                    nodegroup_name=nodegroup_name,
                    login_user=login_user,
                    instance_id=ec2_instance_id,
                    remote_cluster_file=remote_cluster_file
                )
            except Exception as e:
                raise Exception(f"Delete eks cluster failed {e}")

            # terminate ec2 
            try:

                self._aws_services.handle_ec2_action(
                    action=EC2Actions.terminate.name,
                    ec2_instance_id=ec2_instance_id,
                    login_user=login_user,
                )
            except Exception as e:
                raise Exception(f"Terminate ec2 failed {e}")
            # delete key pair
            try:
                self._aws_services.handle_aws_actions(
                    action=AWSActions.delete_keypair.name
                )
            except Exception as e:
                raise Exception(f"Delete keypair failed :{e}")
            # delete security group wait 
            logging.warning("Delete security group not implement")

        else:
            logging.info("Stop ec2")
            self._aws_services.handle_ec2_action(
                action=EC2Actions.stop.name,
                ec2_instance_id=ec2_instance_id,
                login_user=login_user,
            )
            logging.info("Stop ec2 success")

    
    
    def handle_completion(self,event):
        logging.info("handle remove temp project path")
        temp_project_absoult_path = get_absolute_paht_from_project_name(project_name=self._project_name, base_path=self._base_path)
        delete_project_folder(project_path=temp_project_absoult_path)
        end_time =float(time.time())
        total_process_time = int(end_time - float(self._start_time))
        complete_array = [
            ["Applications","Completion"],
            ["Project name",self._project_name],
            ["Total process time",total_process_time],
            ["Action",self._action]

        ]
        table = AsciiTable(complete_array)
        print(table.table)
        return

    def set_project_name(self):
        project_name = generate_project_name_from_project_path(project_path=self._origin_project_path)
        self._project_name = project_name

   
    def copy_origin_project_into_temp_folder(self):

        if self._project_name is None:
            raise ValueError("Project name is None, Set projec name before you execute this function")

        temp_project_absoult_path = get_absolute_paht_from_project_name(project_name=self._project_name, base_path=self._base_path)
        try:
        # if tem project temp does not exist create temp project
            if not os.path.exists(temp_project_absoult_path):
                logging.info(f"Create {temp_project_absoult_path}")
                os.makedirs(temp_project_absoult_path)
            # 3.8+ only!
            shutil.copytree(self._origin_project_path, temp_project_absoult_path, dirs_exist_ok=True) 
            logging.info(f"Copy {self._origin_project_path} to {temp_project_absoult_path} success")
        except Exception as e:
            raise Exception(f"Copy {self._origin_project_path} to {temp_project_absoult_path} failed: {e}")
        return 


    def handle_local_processing(self ,event):
        logging.info("Run command in local machine")
        first_n_file = self._input_answers['process_first_n_files']

        gismoclouddeploy(
            number=first_n_file,
            project = self._project_name,
            aws_access_key=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_region=self.aws_region,
        )
        logging.info("Copy results to origin path")

    def handle_cloud_processing(self,event):
        logging.info("handle cloud process")
        if self._action == MenuActions.run_in_local_machine.name or \
            self._action == MenuActions.cleanup_cloud_resources.name:
            raise Exception(f"Aciton {self._action} should not enter this state. Check your code")
        
        is_ssh = self._input_answers['is_ssh']
        if is_ssh is False:
            process_first_n_files = self._input_answers['process_first_n_files']
            cluster_name = self._eks_config_dict['metadata']['name']
            num_of_nodes = self._input_answers['num_of_nodes']
            run_files_command = generate_run_command_from_inputs(
                is_local= False,
                process_first_n_files=process_first_n_files,
                project_name = self._project_name,
                num_of_nodes=num_of_nodes,
                cluster_name = cluster_name
            )
            # execute run file command 
            ec2_config_file = self.saved_config_path_base +f"/{self._system_id}/config-ec2.yaml"
            if not exists(ec2_config_file):
                raise Exception(f"{ec2_config_file} does not exist")
            ec2_dict = convert_yaml_to_json(yaml_file=ec2_config_file)
            ec2_instance_id = ec2_dict['ec2_instance_id']
            login_user = ec2_dict['login_user']
            key_pair_name = ec2_dict['key_pair_name']
            if ec2_instance_id is None:
                raise Exception("ec2 instance id is None")
            self._aws_services.run_ssh_command(
                login_user=login_user,
                ec2_instance_id=ec2_instance_id,
                ssh_command=run_files_command
            )
        else:
            logging.info("SSH Debug mode")
            self._aws_services.run_ssh_debug_mode()



def delete_project_folder(project_path:str):
    logging.info("Delete project folder")
    if not os.path.exists(project_path):
        raise Exception(f"{project_path} does not exist")
    try:
        shutil.rmtree(project_path)
        logging.info(f"Delete {project_path} success")
    except Exception as e:
        raise Exception(f"Dlete {project_path} failded")

        
def generate_run_command_base_on_input_answers(action:str, input_answers:dict, project_name:str, cluster_name:str, num_of_nodes:int) -> str:
    command = None
    process_first_n_files = 1
    if "process_first_n_files" in input_answers:
        process_first_n_files = input_answers['input_answers']
    else:
        raise Exception("input_answers has no process_first_n_files key")

    if project_name is None:
        raise Exception("project name is None")

    if action == MenuActions.run_in_local_machine.name:
        command = f"python3 main.py run-files -n {process_first_n_files} -p {project_name}"
    if action == MenuActions.create_cloud_resources_and_start.name or action == MenuActions.resume_from_existing.name:
        if (cluster_name or num_of_nodes) is None :
            raise Exception("Cluster name or num of node is None")
        command = f"python3 main.py run-files -n {process_first_n_files} -s {num_of_nodes} -p {project_name} -c {cluster_name}"

    if command is None:
        raise Exception("command is None, Check your work flow.")
    return command

        
def import_and_verify_ec2_config(ec2_config_file:str) -> dict:
    logging.info(f"import from ec2 {ec2_config_file}")
    if ec2_config_file is None:
        raise Exception(f"saved_ec2_config_file is None") 
    if not exists(ec2_config_file):
        raise Exception("saved_ec2_config_file does not exist")
    try:
        config_dict = convert_yaml_to_json(yaml_file=ec2_config_file)
        verify_keys_in_ec2_configfile(config_dict=config_dict)
        return config_dict
    except Exception as e:
        raise e 

def import_from_eks_config(saved_eks_config_file:str)-> dict:
    logging.info("import from eks")
    if saved_eks_config_file is None:
        raise Exception(f"saved_eks_config_file is None") 
    if not exists(saved_eks_config_file):
        raise Exception("saved_eks_config_file does not exist")
    try:
        config_dict = convert_yaml_to_json(yaml_file=saved_eks_config_file)
        verify_keys_in_eks_configfile(config_dict=config_dict)
        return config_dict
    except Exception as e:
        raise e



def handle_proecess_files_inputs_questions(action:MenuActions, default_answer:dict) -> dict:

    return_answer= {}
    try:
        if action == MenuActions.cleanup_cloud_resources.name:
            logging.info("No further more questions in clearn mode!!")
            return
        # project tag
        if action == MenuActions.create_cloud_resources_and_start.name:
            project_in_tags = hanlde_input_project_name_in_tag(
                input_question= InputDescriptions.input_project_name_in_tags.value,
                default_answer = default_answer['project_in_tags']
            )
            # update answer
            return_answer['project_in_tags'] = project_in_tags
    
        if action == MenuActions.create_cloud_resources_and_start.name \
            or action == MenuActions.resume_from_existing.name:
            is_ssh  = handle_yes_or_no_question(
                input_question=InputDescriptions.is_debug_mode_questions.value,
                default_answer=default_answer['is_ssh']
            )
            return_answer['is_ssh'] = is_ssh
            if is_ssh is True:
                return return_answer

        # process files
        process_first_n_files = default_answer['process_first_n_files']
        is_process_all_file = handle_yes_or_no_question(
            input_question=InputDescriptions.is_process_all_files_questions.value,
            default_answer=default_answer['is_process_all_file']
        )
        if is_process_all_file is False:
            process_first_n_files = handle_input_number_of_process_files_question(
                input_question=InputDescriptions.input_the_first_n_files_questions.value,
                default_answer=process_first_n_files,
            )
            return_answer['process_first_n_files'] = process_first_n_files
            logging.info(f"Process first {process_first_n_files} files")
        else:       
            return_answer['process_first_n_files'] = process_first_n_files
            logging.info(f"Process all files: -n {process_first_n_files}")

        

        if action == MenuActions.create_cloud_resources_and_start.name \
            or action == MenuActions.resume_from_existing.name:
            logging.info("Input the number of instances ")
            num_of_nodes = handle_input_number_of_scale_instances_question(
                input_question=InputDescriptions.input_number_of_generated_instances_questions.value,
                default_answer=default_answer['num_of_nodes'],
                max_node= default_answer['max_node']
            )
            return_answer['num_of_nodes'] = num_of_nodes
            logging.info(f"Number of generated instances:{num_of_nodes}")
            
        if action == MenuActions.run_in_local_machine.name:
            return return_answer
        # is clean up after completion 
        cleanup_resources_after_completion = handle_yes_or_no_question(
            input_question=InputDescriptions.is_cleanup_resources_after_completion.value,
            default_answer=default_answer["cleanup_resources_after_completion"]
        )
        return_answer['cleanup_resources_after_completion'] = cleanup_resources_after_completion
    except Exception as e:
        raise Exception (f"handle_proecess_files_inputs_questions error: {e}")

    return return_answer

    


def generate_project_name_from_project_path(project_path:str) -> str:
    project_name = "temp/"+ basename(project_path)
    return project_name

def get_absolute_paht_from_project_name(project_name:str, base_path:str) -> str:
    temp_project_absoult_path =  os.path.join(base_path,project_name)
    return temp_project_absoult_path


def select_created_cloud_config_files(saved_config_path_base:str) -> str:
    '''
    Select created resource config files from a path
    '''
    logging.info("select_created_cloud_config_files")  

    config_lists = get_subfolder(parent_folder=saved_config_path_base)
    questions = [
        inquirer.List('dir',
                        message=InputDescriptions.select_an_created_resources.value,
                        choices=config_lists,
                    ),
    ]
    inst_answer = inquirer.prompt(questions)
    answer =  inst_answer["dir"]
    select_absolute_history_path = saved_config_path_base + f"/{answer}"
    return select_absolute_history_path

 

def get_subfolder(parent_folder) -> list:
    if not os.path.exists(parent_folder):
        raise Exception (f"{parent_folder} does not exis–t")
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




def generate_run_command_from_inputs(
    process_first_n_files:int = 1, 
    cluster_name:str = None, 
    num_of_nodes:str = 1, 
    project_name:str = None, 
    is_local:bool= True) -> str:

    command = None
    if is_local:
        command = f"python3 main.py run-files -n {process_first_n_files} -p {project_name}"
    else:
        command = f"python3 main.py run-files -n {process_first_n_files} -s {num_of_nodes} -p {project_name} -c {cluster_name}"

    if command is None:
        raise Exception("Generated command is None")
        
    return command