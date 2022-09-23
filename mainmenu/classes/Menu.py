
import time
import os
from os.path import  basename, exists
import logging
import inquirer
import shutil
from terminaltables import AsciiTable
from mainmenu.classes.constants.InputDescriptions import InputDescriptions
from .constants.MenuActions import MenuActions
from .utilities.convert_yaml import convert_yaml_to_json
from .utilities.verify_key import verify_a_key_in_dict,verify_keys_in_configfile
from .utilities.handle_inputs import(
    handle_input_project_path_question,
)

from .utilities.aws_utitlties import (
    connect_aws_client,
    get_iam_user_name
)


class Menu(object):
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
        self._saved_ec2_config_file = None,
        self._saved_eks_config_file = None,

        # path 
        self._base_path = os.getcwd()
        self._process_first_n_files = 1
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

        # self._cluster_name = f"gcd-{self._user_id}-{self._start_time}"
        self._cluster_name = None
        self._ec2_name = None
        self._keypair = None
        # self._ec2_name = f"gcd-{self._user_id}-{self._start_time}"
        # self._keypair = f"gcd-{self._user_id}"
        
        self._local_pem_path = local_pem_path 

        # default project 
        self._template_project = self._base_path +"/examples/solardatatools"
        self._project_name = None
        self._temp_project_absoult_path = None
        self._origin_project_path = None


        # ssh command 
        self._runfiles_command = None
        self._is_ssh = False
        
        #confirmation 
        self._is_confirm_to_process = False

    def get_relative_project_folder(self):
        return self._project_name

    def get_cluster_file(self):
        return self._saved_eks_config_file

    def get_cleanup_after_completion(self):
        return self._cleanup_resources_after_completion

    def get_run_files_command(self):
        return self._runfiles_command
    # def get_project_path(self):
    #     return self._temp_project_absoult_path
        
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


    # def get_ec2_export_full_path_name(self):
    #     return self._config_history_path + "/config-ec2.yaml"
    
    # def get_eks_export_full_path_name(self):
    #     return self._config_history_path + "/cluster.yaml"
        
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
        '''
        Select an action from a menu
        '''
        logging.info("Main menus")
        menus_selection =[]
        
        inst_question = [
            inquirer.List('action',
                            message=InputDescriptions.select_an_action.value,
                            choices=[
                                MenuActions.create_cloud_resources_and_start.name,
                                MenuActions.resume_from_existing.name, 
                                MenuActions.cleanup_cloud_resources.name, 
                                MenuActions.run_in_local_machine.name],
                        ),
        ]
        inst_answer = inquirer.prompt(inst_question)
        self._menus_action = inst_answer["action"]
        
        logging.info(f"Set action : {self._menus_action}")

    def select_created_cloud_config_files(self):
        '''
        Select created resource config files from a path
        '''
        logging.info("select_created_cloud_config_files")  

        config_lists = get_subfolder(parent_folder=self.saved_config_path_base)
        questions = [
            inquirer.List('dir',
                            message=InputDescriptions.select_an_created_resources.value,
                            choices=config_lists,
                        ),
        ]
        inst_answer = inquirer.prompt(questions)
        answer =  inst_answer["dir"]
        self._config_history_path = self.saved_config_path_base + f"/{answer}"
        logging.info(f"You have selected saved config path : {self._config_history_path}")
        self.set_relative_saved_config_files_folder_name(name=answer)
        self._saved_ec2_config_file = self._config_history_path +"/config-ec2.yaml"
        self._saved_eks_config_file = self._config_history_path +"/cluster.yaml"
        return 


    def set_relative_saved_config_files_folder_name(self,name):
        self._relative_saved_config_files_folder_name = name

    def get_relative_saved_config_files_folder_name(self):
        return self._relative_saved_config_files_folder_name

    def generate_ec2_name(self):
        if self._ec2_name is None:
            self._ec2_name = f"gcd-{self._user_id}-{self._start_time}"
            return 
        else:
            raise ValueError("Something wring, ec2 name should be None is this state")

    def generate_eks_cluster_name(self):
        if self._cluster_name is None:
            self._cluster_name = f"gcd-{self._user_id}-{self._start_time}"
            return 
        else:
            raise ValueError("Something wring, ec2 name should be None is this state")
    def generate_eks_cluster_name(self):
        if self._cluster_name is None:
            self._cluster_name = f"gcd-{self._user_id}-{self._start_time}"
            return 
        else:
            raise ValueError("Something wring, eks cluster name should be None is this state")
    def generate_keypair_name(self):
        if self._keypair is None:
            self._keypair = f"gcd-{self._user_id}"
            return 
        else:
            raise ValueError("Something wring, keypair name should be None is this state")

    #----------------
    # Initializations
    #----------------
    def hanlde_initialization(self):
        '''
        Initialization system . Verify input config file, import varialbles
        '''
        action = self._menus_action
        if action is None:
            logging.info("Something woring!!, menu action is None")
            return
        logging.info("===============")
        logging.info("Initialization")
        logging.info("===============")

        # step 1 . ask for project
        self.handle_enter_input_project_path()

        # step 2. verify file structures
        if action != MenuActions.cleanup_cloud_resources.name:
            self.handle_verify_project_folder()

        # if action == MenuActions.create_cloud_resources_and_start.name:
        #     logging.info("Creat from new")
        # elif self._menus_action == MenuActions.resume_from_existing.name:
        #     logging.info("Resume from existing")
        # elif self._menus_action == MenuActions.run_in_local_machine.name:
        #     logging.info("Run in local")
        # elif self._menus_action == MenuActions.cleanup_cloud_resources.name:
        #     logging.info("Run delete cloud resources")



    #handle mensu action
    # def handle_prepare_actions(self):
    #     if self._menus_action is None:
    #         raise Exception("No menu action selected , somehting wrong")

    #     if self._menus_action == MenuActions.create_cloud_resources_and_start.name:
    #         logging.info("crete cloud resources and start")
    #         logging.info("Step 1 , input project folder")
    #         self.generate_ec2_name()
    #         self.generate_eks_cluster_name()
    #         self.generate_keypair_name()
    #         self.handle_enter_input_project_path()
    #         logging.info("Step 2 , check file structur corrects")
    #         self.handle_verify_project_folder()
    #         logging.info("Step 3 , input questions")
    #         self.handle_proecess_files_inputs_questions()
    #         logging.info("Step 4 , generate cluster.yaml from tempaltes")
    #         self.generate_config_history_path_and_export_eks_config()
    #         self.handle_input_projet_tags()
    #         self.import_ec2_variables_from_templates()
    #         self.print_variables_and_request_confirmation()



    #     elif self._menus_action == MenuActions.resume_from_existing.name :
    #         logging.info("resume from existing")
    #         logging.info("Step 0 , select saved config file")
    #         self.select_created_cloud_config_files()
    #         logging.info("Step 1 , input project folder")
    #         self.handle_enter_input_project_path()
    #         logging.info("Step 2 , check file structur corrects")
    #         self.handle_verify_project_folder()
    #         self.import_from_ec2_config()
     
    #         self.import_from_eks_config()

    #         logging.info("Step 3 , handle ask question")
    #         self.handle_proecess_files_inputs_questions()
    #         self.print_variables_and_request_confirmation()
 
            


    #     elif self._menus_action == MenuActions.cleanup_cloud_resources.name:
    #         logging.info("clearnup created cloud resources")
    #         logging.info("Step 0 , select saved config file")
    #         self.select_created_cloud_config_files()
    #         logging.info("Step 1 , input project folder")
    #         self.handle_enter_input_project_path()
    #         logging.info("Step 2 , check file structur corrects")
    #         self.handle_verify_project_folder()
    #         self.import_from_ec2_config()
    #         self.import_from_eks_config()
    #         self.print_variables_and_request_confirmation()
            

    #     elif self._menus_action == MenuActions.run_in_local_machine.name:
    #         logging.info("run in local machine")
    #         self.handle_enter_input_project_path()
    #         logging.info("Step 3 , check file structur corrects")
    #         logging.info("Step 3 , handle ask question")

    #         self.handle_verify_project_folder()
    #         self.handle_proecess_files_inputs_questions()
    #         self.print_variables_and_request_confirmation()
    #         print(f"self._project_name,:{self._project_name,}")
    #         # run_process_files(
    #         #     number=self._process_first_n_files,
    #         #     project = self._project_name,
    #         #     scale_nodes= 1,
    #         #     repeat = 1,
    #         #     aws_access_key=self.aws_access_key,
    #         #     aws_secret_access_key=self.aws_secret_access_key,
    #         #     aws_region=self.aws_region,
    #         #     default_fileslist = []
    #         # )


    def print_variables_and_request_confirmation(self):
        if  self._menus_action == MenuActions.run_in_local_machine.name:
            local = [
                ["Parameters","Details"],
                ['project folder', self._project_name],
                ['Temp project path', self._temp_project_absoult_path],
                ['number of process files', self._process_first_n_files],
                ["Command", self._runfiles_command],
            ]
            table = AsciiTable(local)
            print(table.table)
            self._is_confirm_to_process = handle_yes_or_no_question(
            input_question="Comfim to process (must be yes/no)",
            default_answer="yes"
        )
            return 
        # if self._menus_action == MenuAction.create_cloud_resources_and_start.name:

        cloud_resource = [
            ["Parameters","Details"],
            ['project full path', self._temp_project_absoult_path],
            ['project folder', self._project_name],
            ['number of process files', self._process_first_n_files],
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
        if self._menus_action == MenuAction.resume_from_existing.name:
            ec2_config_dict = convert_yaml_to_json(yaml_file=self._saved_ec2_config_file)
            self._ec2_tages = ec2_config_dict['tags']
            self._ec2_image_id = ec2_config_dict['ec2_image_id']
            self._ec2_instance_type = ec2_config_dict['ec2_instance_type']
            self._ec2_volume = ec2_config_dict['ec2_volume']
            self.key_pair_name = ec2_config_dict['key_pair_name']
            self._ec2_instance_id = ec2_config_dict['ec2_instance_id']
        ec2_resources = [
            ["Parameters","Details"],
            ['ec2_tags', self._ec2_tages],
            ['ec2 image id', self._ec2_image_id],
            ['ec2 instances type', self._ec2_instance_type],
            ['ec2 volume', self._ec2_volume],
            ['ec2 keypair', self._keypair],
            ['pem location', self._local_pem_path],
            ['ec2 instance id', self._ec2_instance_id],

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
        if self._cluster_name is None:
            self._cluster_name = self._eks_config_yaml_dcit['metadata']['name']
        else:
            raise ValueError("cluster name should be None in this state, Please check your code.")
        verify_keys_in_eks_configfile(config_dict=self._eks_config_yaml_dcit)


    def handle_input_projet_tags(self):
        logging.info("Project tags")
        self._project_in_tags = hanlde_input_project_name_in_tag(
            input_question= InputQuestions.input_project_name_in_tags.value,
            default_answer = self._project_in_tags
    
        )
        return 

    def handle_proecess_files_inputs_questions(self):
        if self._menus_action == MenuAction.create_cloud_resources_and_start.name or self._menus_action == MenuAction.resume_from_existing.name:
            self._is_ssh  = handle_yes_or_no_question(
                input_question=InputQuestions.is_debug_mode_questions.value,
                default_answer="no"
            )

        logging.info("Process all files in buckets?")
        if self._is_ssh is True:
            return 

        # if not debug mode

        is_process_all_file = handle_yes_or_no_question(
            input_question=InputQuestions.is_process_all_files_questions.value,
            default_answer="no"
        )
        if is_process_all_file is False:
            self._process_first_n_files = handle_input_number_of_process_files_question(
                input_question=InputQuestions.input_the_first_n_files_questions.value,
                default_answer=1,
            )
        else:
            
            self._process_first_n_files = 0
            logging.info(f"Process all files: -n {self._process_first_n_files}")

        logging.info(f"Process first {self._process_first_n_files} files")

        if self._menus_action == MenuAction.create_cloud_resources_and_start.name or self._menus_action == MenuAction.resume_from_existing.name:
            logging.info("Input the number of instances ")
            self._num_of_nodes = handle_input_number_of_scale_instances_question(
                input_question=InputQuestions.input_number_of_generated_instances_questions.value,
                default_answer=1,
                max_node= self._max_nodes
            )
            logging.info(f"Number of generated instances:{self._num_of_nodes}")
        
        # generate run files command 
        if self._menus_action == MenuAction.create_cloud_resources_and_start.name or self._menus_action == MenuAction.resume_from_existing.name:
            self._runfiles_command = f"python3 main.py run-files -n {self._process_first_n_files} -s {self._num_of_nodes} -p {self._project_name} -c {self._cluster_name}"
        elif self._menus_action == MenuAction.run_in_local_machine.name:
            self._runfiles_command = f"python3 main.py run-files -n {self._process_first_n_files} -p {self._project_name}"

        return 


    def handle_enter_input_project_path(self):
        '''
        input project path
        '''
        default_project = self._template_project
        self._origin_project_path = handle_input_project_path_question(
            input_question=InputDescriptions.input_project_folder_questions.value,
            default_answer=default_project
        )
        self._project_name = basename(self._origin_project_path)
        self._temp_project_absoult_path = self._base_path + f"/temp/{self._project_name}"

        logging.info(f"Copy {self._origin_project_path} to {self._temp_project_absoult_path}")

        if not os.path.exists(self._temp_project_absoult_path):
            logging.info(f"Create {self._temp_project_absoult_path}")
            os.makedirs(self._temp_project_absoult_path)
        shutil.copytree(self._origin_project_path, self._temp_project_absoult_path, dirs_exist_ok=True)  # 3.8+ only!



    def handle_verify_project_folder(self):
        files_check_list = ["entrypoint.py","Dockerfile","requirements.txt","config.yaml"]
        for file in files_check_list:
            
            full_path_file = self._temp_project_absoult_path + "/"+file
            if not exists(full_path_file):
                raise Exception(f"{full_path_file} does not exist!!")
            logging.info(f"{file} exists !!")
            
        logging.info("Verify files list success")
        config_yaml = self._temp_project_absoult_path + "/config.yaml"
        try:
            self._config_yaml_dcit= convert_yaml_to_json(yaml_file=config_yaml)
        except Exception as e:
            raise Exception(f"convert config yaml failed")
        verify_keys_in_configfile(
            config_dict=self._config_yaml_dcit
        )
        # verify solver 
        logging.info("Verify solver")
        

        
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
        if not os.path.exists(self._temp_project_absoult_path):
            raise Exception(f"{self._temp_project_absoult_path} does not exist")
        try:
            shutil.rmtree(self._temp_project_absoult_path)
        except Exception as e:
            raise Exception(f"Dlete {self._temp_project_absoult_path} failded")


        
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


