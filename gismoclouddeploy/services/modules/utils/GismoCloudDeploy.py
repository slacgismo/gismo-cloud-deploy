from cmath import log
from enum import Enum
from transitions import Machine
from .modiy_config_parameters import modiy_config_parameters, convert_yaml_to_json
import enum
import os
import logging
from os.path import exists
# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

class Environments(enum.Enum):
    LOCAL = 0
    AWS = 1

class GismoCloudDeploy(object):

    states=['stop', 
            'load_config', 
            'prepare_system',
            'build_tag_images',
            'deploy_k8s',
            'send_command_to_servers',
            'long_pulling_sqs',
            'clean_services',
            'analyzing_logs',
            ]

    def __init__(
            self, 
            configfile, 
            env, 
            num_inputfile:int = 1,
            aws_access_key: str = None,
            aws_secret_access_key: str = None,
            aws_region: str = None,
        ) -> None:

        self.configfile = configfile
        self.env = env.upper()
        self.num_inputfile = num_inputfile
        self.aws_access_key = aws_access_key,
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region

        self._repeat_index = 0
        #eks properties
        self.cluster_name = None   
        self.nodegroup_name = None   
        self.instanceType = None     

        #k8s parameters
        self.k8s_namespace_set = set()
        self.separated_process_file_list_in_servers = []
        self.config = {}
        

        # add handle error state 
        # self.machine = Machine(model=self, states=GismoCloudDeploy.states, initial='stop', on_exception='handle_error', send_event=True)
        self.machine = Machine(model=self, states=GismoCloudDeploy.states, initial='stop', on_exception='handle_error',send_event=True)
        
        self.machine.add_transition(trigger='trigger_load_config', source='stop', dest='load_config', after='handle_read_config_yaml')
        self.machine.add_transition(trigger='trigger_prepare_system', source='load_config', dest='prepare_system', after='handle_prepare_system')
        self.machine.add_transition(trigger='trigger_build_and_tag_images', source='prepare_system', dest='build_tag_images', before ='handle_build_and_tag_images',after='handle_push_images_to_cloud')
        self.machine.add_transition(trigger='trigger_deploy_k8s', source='build_tag_images', dest='deploy_k8s', before='handle_deploy_k8s',after='handle_verify_k8s_services')
        self.machine.add_transition(trigger='trigger_send_command_to_servers', source='deploy_k8s', dest='send_command_to_servers', after='handle_send_command_to_server')
        self.machine.add_transition(trigger='trigger_long_pulling_sqs', source='send_command_to_servers', dest='long_pulling_sqs', after='handle_long_pulling_sqs')
        self.machine.add_transition(trigger='trigger_clean_services', source='*', dest='stop', before='handle_clean_services', 
        after='handle_analyzing_logs')

    def save_file(self, file_name, env, file_path_local, file_path_cloud):
        """ return full saved file name and path based on env"""
        file_path_name = ""
            
        if env == Environments.AWS.name:
            file_path_name = file_path_cloud +"/"+ file_name
        else:
            # check if directory exist 
            if not os.path.exists(file_path_local):
                logger.info(f"{file_path_local} does not exist. Create {file_path_local}")
                os.mkdir(file_path_local)
            file_path_name = file_path_local +"/"+ file_name
            
        return file_path_name   
          
    def add_namespace(self, namespace):
        # add namespace into property set
        self.k8s_namespace_set.add(namespace)
    
    def remove_namespace(self, namespace):
        self.k8s_namespace_set.remove(namespace)
    
    def remove_all_namespace(self, namespace):
        self.k8s_namespace_set.removeall()

    def add_server_pod_name(self, podname):
        self.podname_of_server_dict

    # process files
    def add_separated_process_file_list_in_servers(self, files_list):
        self.separated_process_file_list_in_servers.append(files_list)
    
    

    def raise_error(self, event): raise ValueError("Oh no")

    def handle_error(self, event):
        print("Fixing things ...")
        if self.is_aws():
            print("handle error on AWS")
        elif self.is_local():
            print("handle error on LOCAL")

        print(event.error)
        # del event.error  # it did not happen if we cannot see it ...


    def is_aws(self) -> bool:
        if self.env == Environments.AWS.name:
            return True
        return False

    def is_local(self) -> bool:
        if self.env == Environments.LOCAL.name:
            return True
        return False

    # state function

    def handle_read_config_yaml(self,event):
        config_yaml = f"./config/{self.configfile}"
        if exists(self.configfile) is False:
            logger.warning(
                f"{config_yaml} not exist, use default config.yaml instead"
            )
        try:
            self.config = convert_yaml_to_json(yaml_file=config_yaml)
        except Exception as e:
            raise e

    def handle_prepare_system(self, event):
        print("handle_prepare_system")
    
    def handle_build_and_tag_images(self, event):    
        print("handle_build_and_tag_images")

    def handle_push_images_to_cloud(self, event):
        print("handle_push_images_to_cloud")
    
    def handle_deploy_k8s(self, event):
        print("handle_deploy_k8s")
    
    def handle_verify_k8s_services(self, event):
        print("handle_verify_k8s_services")
    
    def handle_send_command_to_server(self, event):
        print("handle_send_command_to_server")

    def handle_long_pulling_sqs(self, event):
        print("handle_long_pulling_sqs")
    
    
    def handle_clean_services(self, event):
        print("handle_clean_services")

    
    def handle_analyzing_logs(self, event):
        print("handle_analyzing_logs")


    @property
    def repeat_index(self) -> int:
        return self._repeat_index 
    

# lump = GismoCloudDeploy()
# m = Machine(lump, states, before_state_change='raise_error', on_exception='handle_error', send_event=True)
# try:
#     lump.to_gas()
# except ValueError:
#     pass
# print(lump.state)