
from distutils import log
from enum import Enum

import fnmatch
import re
from transitions import Machine
from .modiy_config_parameters import convert_yaml_to_json
from .check_aws import check_aws_validity
import enum
from .initial_end_services import initial_end_services
from .long_pulling_sqs import long_pulling_sqs_multi_server
import os
import coloredlogs, logging
from os.path import exists
import re
import socket
import boto3
import math
import time
import threading
from .eks_utils import scale_eks_nodes_and_wait, wait_pod_ready
import json
from .command_utils import verify_keys_in_configfile
from .invoke_function import (
    invoke_docker_compose_build,
    invoke_tag_image,
    invoke_ecr_validation,
    invoke_push_image,
    invoke_eks_updagte_kubeconfig,
    # invoke_process_files_to_server_namespace,
    invoke_exec_k8s_run_process_files,
    # invoker_check_docker_running
    
    
)

from .process_log import analyze_all_local_logs_files,process_logs_from_local
from .k8s_utils import (
    check_k8s_services_exists, 
    create_k8s_svc_from_yaml,
    get_k8s_pod_name_from_namespace,
    k8s_create_namespace,
)

from typing import List
from .check_aws import (
    connect_aws_client,
    connect_aws_resource,
)

from .sqs import (

    create_queue,
)
from .command_utils import (

    create_or_update_k8s_deployment,
)
import coloredlogs, logging
coloredlogs.install()

class Environments(enum.Enum):
    LOCAL = 0
    AWS = 1

class GismoCloudDeploy(object):
    states=[
        'system_stop', 
        'system_initial',
        'system_ready',
        'system_deploy',
        'system_processing',
        ]


    def __init__(
            self, 
            project, 
            env, 
            scale_nodes:int = None,
            num_inputfile:int = 1,
            repeat:int = 1,
            aws_access_key: str = None,
            aws_secret_access_key: str = None,
            aws_region: str = None,
            ecr_repo: str = None,
            instance_type :str = None,
            nodegroup_name:str = None,
            cluster:str = None,
            default_fileslist :list = []
            
        ) -> None:
        self.project = project
        self.env = env.upper()
        self.num_inputfile = num_inputfile
        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.ecr_repo = ecr_repo
        
   
        #eks properties
        self._cluster_file = ""
        self._scale_eks_nodes_wait_time  = 1
        self._interval_of_wait_pod_ready  = 1
        self._cluster_name = cluster
        self._nodes_maxSize = 100 # this is the limit from AWS
        
        self._nodegroup_name = nodegroup_name
        self._instanceType = instance_type
        self._total_num_nodes = scale_nodes
        # self._ec2_bastion_saved_config_file = ""

        # private variables
        self._k8s_namespace_set = set()
        self._separated_process_file_list_in_servers = {}
        self._config = {}
        self._saved_path_cloud = ""
        self._saved_path_local = ""
        self._repeat_number_per_round = 1
        self._is_celeryflower_on = False
        self._repeat_index = 0
        self._user_id = ""
        self._host_name = ""
        self._sqs_url = ""

        self._code_template_folder = ""

        self._data_bucket = ""
        self._saved_bucket = ""
        self._default_files  = default_fileslist
        
        self._process_column_keywords = ""
        self._file_pattern = "*.csv"
        self._num_namesapces = 1
        self._num_worker_pods_per_namespace = 8
        self._total_number_files = 0
        self._worker_desired_replicas = 1
        self._services_config_list = {}
        self._filename = {}
        self._ready_server_list = []
        self._acccepted_idle_time = 360
        self._interval_of_checking_sqs = 3

        self._save_file_absoulte_path_local =""
        self._save_file_absoulte_path_cloud =""
        self._saved_file_local = {}
        self._start_time = time.time()
        self._initial_process_time = 0
        self._total_process_time = 0 
        self._num_repetion = repeat
        self._unfinished_tasks_id_set = set()
        self._init_process_time_list = []
        self._total_proscee_time_list = []
        self._upload_file_dict = dict()
        self._upload_file_name = None
        self._upload_files_local_path = None
        self._upload_files_target_path = None
        self._solver_lic_file_name = None
        self._solver = None

        self._base_path = os.getcwd()
  
        self.machine = Machine(model=self, states=GismoCloudDeploy.states, initial='system_stop', on_exception='handle_error',send_event=True)
        self.machine.add_transition(trigger='trigger_initial', source='system_stop', dest='system_initial', before ='handle_read_config_yaml', after='handle_prepare_system')
        self.machine.add_transition(trigger='trigger_ready', source='system_initial', dest='system_ready', before ='handle_build_and_tag_images', after='handle_push_images_to_cloud')
        self.machine.add_transition(trigger='trigger_deploy', source='system_ready', dest='system_deploy', before ='handle_deploy_k8s', after='handle_verify_k8s_services')
        self.machine.add_transition(trigger='trigger_processing', source='system_deploy', dest='system_processing', before ='handle_send_command_and_long_polling_sqs')
        self.machine.add_transition(trigger='trigger_cleanup', source='*', dest='system_stop', before ='handle_clean_services', after = 'handle_analyzing_logs')
        self.machine.add_transition(trigger='trigger_repetition', source='system_processing', dest='system_initial',conditions=['is_repeatable'], before="increase_repeat_index")


        
    def is_repeatable(self, evnet):
       
        return (self._repeat_index < self._num_repetion)
    
    def increase_repeat_index(self,event):
        self._repeat_index += 1
        return self._repeat_index



    def get_num_repetition(self) -> int:
        return self._num_repetion
        
    def get_repeat_index(self) -> int:
        return self._repeat_index 

    def handle_error(self, event):
        raise ValueError(f"Oh no {event.error}") 


    def _is_aws(self) -> bool:
        if self.env == Environments.AWS.name:
            return True
        return False

    def _is_local(self) -> bool:
        if self.env == Environments.LOCAL.name:
            return True
        return False


    

    def handle_read_config_yaml(self,event):
      
        config_yaml = f"{self._base_path}/projects/{self.project}/config.yaml"

        if exists(config_yaml) is False:
            # logging.error(
            #     f"{config_yaml} not exist, use default config.yaml instead"
            # )
            raise Exception(f"{config_yaml} does not exist.")
        try:
            
            self._config = convert_yaml_to_json(yaml_file=config_yaml)
  
            # assert keys  in configfile
            verify_keys_in_configfile(self._config)
            logging.info("=== Pass assert key test ======")
            # services list
            k8s_configfile =  f"{self._base_path}/config/k8s/config-k8s.yaml"
            if not exists(k8s_configfile):
                raise Exception(f"{k8s_configfile} does not exist.")

            k8s_config =  convert_yaml_to_json(yaml_file=k8s_configfile)
            self._services_config_list = k8s_config["services_config_list"]
            # worker config
            # worker_config = self._config
            self._data_bucket = self._config["data_bucket"]
            self._file_type = self._config["file_pattern"]

            if 'solver' in self._config:
                self._solver = self._config['solver']
            if self._solver is not None:
                self._solver_name = self._solver['solver_name']
                self._solver_lic_local_path = self._solver['solver_lic_local_path']
                self._solver_lic_target_path = self._solver['solver_lic_target_path']
                self._solver_lic_file_name = self._solver['solver_lic_file_name']

            self._code_template_folder  =  self._config["code_template_folder"]
            self._saved_path_cloud = self._config["saved_path_cloud"]
            self._saved_path_local = self._config["saved_path_local"]
            
            self._repeat_number_per_round = self._config["repeat_number_per_round"]
            self._is_celeryflower_on = self._config["is_celeryflower_on"]
            self._num_worker_pods_per_namespace = self._config["num_worker_pods_per_namespace"]
            self._filename = self._config["filename"]
            self._acccepted_idle_time = self._config["acccepted_idle_time"]
            self._interval_of_checking_sqs = self._config["interval_of_checking_sqs"]
            self._process_column_keywords = self._config['process_column_keywords']
            self._saved_bucket = self._config['saved_bucket']


            # for key in self._filename.keys():
            #     self.files_name_key.append(key)

            self._host_name = (socket.gethostname())
            self._user_id = re.sub('[^a-zA-Z0-9]', '', self._host_name).lower()
            self._saved_file_local = {}

            for key, value in self._filename.items():
                self._saved_file_local[key] = []
            # if not exists(self._saved_path_local):
            #     logging.info(f"Make dir {self._saved_path_local} ")
            #     os.makedirs(self._saved_path_local)
            logging.info(f"Remove previous files in {self._saved_path_local} folder")
      
            absolute_saved_file_path = self._base_path +f"/projects/{self.project}/"+self._saved_path_local
            if not exists(absolute_saved_file_path):
                logging.info(f"Make dir {absolute_saved_file_path} ")
                os.makedirs(absolute_saved_file_path)
            
            # remove all the previous file
            for f in os.listdir(absolute_saved_file_path):
                os.remove(os.path.join(absolute_saved_file_path, f))

            self._save_file_absoulte_path_local = absolute_saved_file_path
            self._save_file_absoulte_path_cloud = self._saved_path_cloud +"/" +self._user_id 
            print(f"save local {self._save_file_absoulte_path_local}")
            # check if upload file path exist. if not create a empty license
            


        
            self._cluster_file  = f"{self._base_path}/projects/{self.project}/cluster.yaml"
            self._scale_eks_nodes_wait_time  = self._config['scale_eks_nodes_wait_time']
            self._interval_of_wait_pod_ready  = self._config['interval_of_wait_pod_ready']
          
        except Exception as e:
            raise Exception(f"parse config file error :{e}")


        
        try:
            check_aws_validity(key_id=self.aws_access_key, secret=self.aws_secret_access_key)
        except Exception as e:
            logging.error(f"AWS credential failed: {e}")
        return

    def handle_prepare_system(self, event):


        s3_client = boto3.client(
            "s3",
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_access_key,
        )

        print(f"======={self._default_files}")
        # define total process files accourding to input command
        n_files = return_process_filename_base_on_command_and_sort_filesize(
            first_n_files=self.num_inputfile,
            bucket=self._data_bucket,
            default_files=self._default_files ,
            s3_client=s3_client,
            file_pattern=self._file_pattern,
            )
        

        self._total_number_files = len(n_files)
        self._num_namesapces = math.ceil( self._total_num_nodes / self._num_worker_pods_per_namespace )
        num_files_per_namespace =  math.ceil(self._total_number_files/self._num_namesapces)

        # define how many worker pods replcas in each namespaces. 

        self._worker_desired_replicas_per_namespaces =  self._num_worker_pods_per_namespace - 1
        if self._worker_desired_replicas_per_namespaces < 1 :
            self._worker_desired_replicas_per_namespaces = 1
        
        for i in range(self._num_namesapces ):
            curr_time = int(time.time())
        
            namespace = f"{curr_time}-"+ self._user_id  
            self._k8s_namespace_set.add(namespace)


        # assign process file into each namespace.
        _index = 0
        start_index = 0 
        end_inedx = num_files_per_namespace
        process_files_list_per_server_dict = {}
        for namespace in self._k8s_namespace_set:
            _files_list = n_files[start_index : end_inedx]
            process_files_list_per_server_dict[namespace] = _files_list 
            start_index = end_inedx
            end_inedx += num_files_per_namespace
            _index += 1
        if end_inedx < len(n_files):
            raise Exception(f"Assign files to namesapcce error: {end_inedx} < {len(n_files)}")
        self._separated_process_file_list_in_servers = process_files_list_per_server_dict


        for key, value in self._separated_process_file_list_in_servers.items():
            logging.info(f"namespaces : {key} ; num of files {len(value)}")
        
        # create sqs
        sqs_name = f"gcd-{self._user_id}"
        sqs_resource = connect_aws_resource(
            resource_name="sqs",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        
        _resp = create_queue(
            queue_name=sqs_name,
            delay_seconds="0",
            visiblity_timeout="60",
            sqs_resource=sqs_resource,
            tags={"project": "pvinsight"},
        )
        self._sqs_url = _resp.url
        logging.info(f"======== Create {self._sqs_url} success =======")
        


        if self._is_celeryflower_on is False and "celeryflower" in self._services_config_list:
            self._services_config_list.pop('celeryflower')
            logging.info("Remove celerey flower from service list")
         

        
        # update aws parameters 
        if self._is_local():
            print("---------------RUNNING LOCAL")
            # update image rag 
            for service_name in self._services_config_list:
                if service_name == "worker" \
                    or service_name =="server" \
                    or service_name == "celeryflower":
                    # update pull policy
                    self._services_config_list[service_name]['imagePullPolicy'] = "IfNotPresent"
                
        elif self._is_aws():
            print("---------------RUNNING AWS")
            for service_name in self._services_config_list:
                if service_name == "worker" \
                    or service_name =="server" \
                    or service_name == "celeryflower":
                    # update pull policy
                    # self._services_config_list[service_name]['imagePullPolicy'] = "Always"
                    updated_name = update_image_tags_for_ecr(
                        service_name=service_name,
                        ecr_repo=self.ecr_repo,
                    )
                    self._services_config_list[service_name]['image_name'] = updated_name
                    self._services_config_list[service_name]['image_tag'] = self._user_id
                logging.info(f"{service_name} : {updated_name}")


    

        return 



    def handle_build_and_tag_images(self, event):    
        logging.info("handle_build_and_tag_images")

        # Should check the docker server is running.
        # if not invoker_check_docker_running():
        #     raise Exception("Docker is not running")
        # docker build image

        if self._solver is None:
            logging.info("No upload file, create a dummy path")
            self._solver_lic_local_path = "dummy"
            self._solver_lic_target_path = "/root/dummy"
            # check if license exist
  
            dummy_full_path = self._base_path +f"/projects/{self.project}/{self._solver_lic_local_path}"
            print(f"Create dummy path {dummy_full_path}")
            if not os.path.exists(dummy_full_path):
                access_rights = 0o755 
                os.mkdir(dummy_full_path, access_rights)


        try:
            invoke_docker_compose_build(
                        project= self.project ,
                        target_path_of_upload_file = self._solver_lic_target_path,
                        source_path_of_upload_file = self._solver_lic_local_path
                    )
            if self._solver_lic_local_path == "dummy":
                logging.info("Remove the dummy path")
                os.rmdir(dummy_full_path)
        except Exception as e:
            
            raise Exception(f"Build Image Failed {e}")

        # update image tag of aws for ecr
        # loac images don't need to update image tags
        if self._is_aws():
            for service in self._services_config_list:
                if service == "worker" or service == "server" or  service == "celeryflower":
                    if self._is_celeryflower_on is False and service == "celeryflower":
                        logging.info("Celery flower is off")
                        continue
                    # Updated image tag
                    update_image = f"{self.ecr_repo}/{service}" 
                    # tag image with user_id
                    invoke_tag_image(
                            origin_image=service,
                            update_image=update_image,
                            image_tag=self._user_id,
                        )
        return 

    def handle_push_images_to_cloud(self, event):
        logging.info("handle_push_images_to_cloud")
        if self._is_aws():
            logging.info("Validate ECR repo")
            try:
                validation_resp = invoke_ecr_validation(ecr_repo=self.ecr_repo)
            except Exception as e:
                raise Exception(f"Validation ECR failed!!")

            logging.info("PUSH images to ECR")
            

            push_thread = list()
            try:
                for service in self._services_config_list:
                    logging.info(f"Push image to {self.ecr_repo}/{service}:{self._user_id}")
                    x = threading.Thread(
                            target=invoke_push_image,
                            args=(service, self._user_id, self.ecr_repo),
                        )
                    x.name = service
                    push_thread.append(x)
                    x.start()
            except Exception as e:
                raise Exception(f"Push images failed")
            
            for index, thread in enumerate(push_thread):
                    thread.join()
                    logging.info("Wait push to %s thread done", thread.name)
                  
        return 
    def handle_deploy_k8s(self, event):
        logging.info("handle_deploy_k8s")

        if self._is_aws():
            logging.info("Update eks config ")
            # update aws eks
            invoke_eks_updagte_kubeconfig(cluster_name=self._cluster_name)
            try:
                logging.info("Scale up eks nodes ")
                scale_eks_nodes_and_wait(
                    scale_node_num=self._total_num_nodes,
                    total_wait_time=self._scale_eks_nodes_wait_time,
                    delay=1,
                    cluster_name=self._cluster_name,
                    nodegroup_name=self._nodegroup_name,
                )
                
            except Exception as e:
                raise Exception("Scale nodes error")

        ## ================== ##
        ## Create neamespaces
        ## ================== ##
        logging.info("Create k8s namespace")
        for namespace in self._k8s_namespace_set:    
            k8s_create_namespace(namespace=namespace)

        # update k8s deployment 

        logging.info("Apply k8s deployment, services in namespace")
        for namespace in self._k8s_namespace_set:   
            for key, value in self._services_config_list.items():
                service_name = key
                if service_name == "celeryflower" and self._is_celeryflower_on is False:
                    continue
                
                deployment_file = self._base_path +"/"+ value["deployment_file"]
                
                desired_replicas = value["desired_replicas"]
                image_base_url = value["image_name"]
                image_tag = value["image_tag"]
                imagePullPolicy = value["imagePullPolicy"]
                print(f"service_name {service_name} image_base_url: {image_base_url}:{image_tag}")
                # create deployment 
                create_or_update_k8s_deployment(
                            service_name=service_name,
                            image_tag=image_tag,
                            image_base_url=image_base_url,
                            imagePullPolicy=imagePullPolicy,
                            desired_replicas=desired_replicas,
                            k8s_file_name=deployment_file,
                            namespace=namespace,
                        )
                # Apply services
                if  "service_file" in value :
                    service_file = self._base_path +"/" +value["service_file"]
                    logging.info(f"Apply {deployment_file} services :{service_name} in namspace:{namespace} ")
                    # check service exist
                    if not check_k8s_services_exists(name=service_name, namspace = namespace):
                        logging.info(
                            f" Apply {service_file} services in namespace: {namespace}"
                        )
                        create_k8s_svc_from_yaml(full_path_name=service_file, namspace=namespace)
                        # create_k8s_svc_from_yaml(full_path_name=service_file, namespace= namespace)
                logging.info(f"End create service :{service_name} in namspace:{namespace} ")

    def handle_verify_k8s_services(self, event):
        logging.info("handle_verify_k8s_services")
        
        # threads = list()
        # try:
        #     for service, value in self._services_con string indices must be integersfig_list.items():
        #         desired_replicas = value["desired_replicas"]
        #         logging.info(f"{service}: desired_replicas: {desired_replicas}")
        #         wait_pod_ready(
        #             num_container=desired_replicas,
        #             container_prefix=service,
        #             counter=self._interval_of_wait_pod_ready,
        #             delay= 1
        #         )
        #         # x = threading.Thread(
        #         #     target=wait_pod_ready,
        #         #     args=(
        #         #         desired_replicas,
        #         #         service,
        #         #         self._interval_of_wait_pod_ready,
        #         #         1,
        #         #     ),
        #         # )
        #         # x.name = service
        #         # threads.append(x)
        #         # x.start()
        # except Exception as e:
        #     raise Exception(f"Verify k8 services failed")

        # logging.info("get server's pod name in each namespace")

        ready_server_list = []
        wait_time = 25
        delay = 5
        while wait_time > 0:
            logging.info(f"K8s reboot Wait {wait_time} sec")
            time.sleep(delay)
            wait_time -= delay

        for namespace in self._k8s_namespace_set:
            server_name = get_k8s_pod_name_from_namespace(pod_name_prefix="server", namespace= namespace)
            if server_name is None:
                continue
            _server_info = {'name': server_name, 'namespace':namespace}
            ready_server_list.append(_server_info)

        if len(ready_server_list) != len(self._k8s_namespace_set):
            raise Exception(f"one of the namespace has no server ready")
        self._ready_server_list = ready_server_list
        logging.info(f"ready server list {ready_server_list}")
        return
    


    def handle_send_command_and_long_polling_sqs(self, event):
        logging.info("handle_send_command_to_server and long_pulling_sqs")
        
        send_command_to_server(
            read_server_list=self._ready_server_list,
            files_list_in_namespace=self._separated_process_file_list_in_servers,
            sqs_url=self._sqs_url,
            aws_access_key=self.aws_access_key,
            aws_secret_access_key= self.aws_secret_access_key,
            aws_region=self.aws_region,
            repeat_number_per_round=self._repeat_number_per_round,
            file_pattern=self._file_pattern,
            data_bucket=self._data_bucket,
            process_column_keywords=self._process_column_keywords,
            solver=self._solver,
            user_id=self._user_id
        )

        
        # generate files name 
        _temp_file_local_dict = {}
        
        
        for key in  self._filename.keys():
            _file_name_local=  upate_filename_path_with_repeat_index(
                absolute_path=self._save_file_absoulte_path_local,
                filename=self._filename[key],
                repeat_index=self._repeat_index
            )
            _temp_file_local_dict[key] = _file_name_local

            # store local file name and path
            if key in self._saved_file_local:
                self._saved_file_local[key].append(_file_name_local)
            else:
                self._saved_file_local[key] = [_file_name_local]

        self._initial_process_time = time.time() - self._start_time
        self._init_process_time_list.append(self._initial_process_time)
        self._unfinished_tasks_id_set = long_pulling_sqs_multi_server(
            save_data_file_path_name =_temp_file_local_dict['saved_data'],
            save_logs_file_paht_name =_temp_file_local_dict['logs_data'],
            errors_file_path_name = _temp_file_local_dict['error_data'],
            delay=self._interval_of_checking_sqs,
            sqs_url=self._sqs_url,
            acccepted_idle_time=self._acccepted_idle_time,
            aws_access_key=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_region=self.aws_region,
            server_list = self._ready_server_list
        )
        
        # process logs and generate gantts 

        process_logs_from_local(
            logs_file_path_name_local = _temp_file_local_dict['logs_data'],
            saved_image_name_local= _temp_file_local_dict['runtime_gantt_chart'],
        )

        #update files to s3 
        for key in self._filename.keys():
            _file_name_cloud=  upate_filename_path_with_repeat_index(
                absolute_path=self._save_file_absoulte_path_cloud,
                filename=self._filename[key],
                repeat_index=self._repeat_index
            )
            # check if local file exists 
            if exists(_temp_file_local_dict[key]):
                logging.info(f"Upload {_temp_file_local_dict[key]}")
                upload_file_to_s3(
                    bucket = self._saved_bucket,
                    source_file_local=_temp_file_local_dict[key],
                    target_file_s3=_file_name_cloud,
                    aws_access_key=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_access_key,
                    aws_region=self.aws_region,
                )
        self._total_proscee_time =  time.time() - self._start_time
        self._total_proscee_time_list.append(self._total_proscee_time)
        return 
       


    # def handle_long_pulling_sqs(self, event):
    #     logging.info("handle_long_pulling_sqs")
        # delay = aws_config_obj.interval_of_check_dynamodb_in_second
        # acccepted_idle_time = int(worker_config_obj.acccepted_idle_time)
        # unfinished_tasks_id_set = long_pulling_sqs_multi_server(
        #     saved_file_dict_local=self._saved_file_list_local,
        #     delay=self._interval_of_checking_sqs,
        #     sqs_url=self._sqs_url,
        #     acccepted_idle_time=self._acccepted_idle_time,
        #     aws_access_key=self.aws_access_key,
        #     aws_secret_access_key=self.aws_secret_access_key,
        #     aws_region=self.aws_region,
        #     server_list = self._ready_server_list
        # )
        # self._initial_process_time = time.time() - self._start_time

    
    
    def handle_clean_services(self, event):
        logging.info("handle_clean_services")
        initial_end_services(
            server_list=self._ready_server_list,
            services_config_list=self._services_config_list,
            aws_access_key=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_region=self.aws_region,
            scale_eks_nodes_wait_time=self._scale_eks_nodes_wait_time,
            cluster_name=self._cluster_name,
            nodegroup_name=self._nodegroup_name,
            sqs_url=self._sqs_url,
            initial_process_time= self._initial_process_time
        )

    def generate_report(self, event):
        logging.info("generate_report")
    def handle_analyzing_logs(self, event):
        logging.info("handle_analyzing_logs")

        # logs_file_list = self._saved_file_local['logs_data']
        analyze_all_local_logs_files(
            project = self.project,
            instanceType=self._instanceType,
            num_namspaces = self._num_namesapces,
            init_process_time_list=self._init_process_time_list,
            total_proscee_time_list=self._total_proscee_time_list,
            eks_nodes_number=self._total_num_nodes,
            num_workers=self._worker_desired_replicas,
            logs_file_path=self._save_file_absoulte_path_local,
            performance_file_txt=self._save_file_absoulte_path_local +"/" +self._filename['performance'],
            num_unfinished_tasks=0,
            code_templates_folder=self._code_template_folder,
            repeat_number=self._num_repetion,

        )
        # update performance 
        upload_file_to_s3(
            bucket = self._saved_bucket,
            source_file_local=self._save_file_absoulte_path_local +"/" +self._filename['performance'],
            target_file_s3=self._save_file_absoulte_path_cloud + "/" + self._filename['performance'],
            aws_access_key=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_region=self.aws_region,
        )
        return 

def genereate_report():
    logging.info("Generate report")

# def upload_all_files_to_s3(

# ):

def list_files_in_bucket(bucket_name: str, s3_client, file_pattern: str):
    """Get filename and size from S3 , fillter file format file"""
    try:

        response = s3_client.list_objects_v2(Bucket=bucket_name)
        files = response["Contents"]
        filterFiles = []
        tet= []
        for file in files:
            filename = file["Key"]
 
            matches = fnmatch.fnmatch(filename, file_pattern)
            
            if matches:
                obj = {
                    "Key": file["Key"],
                    "Size": file["Size"],
                }
                filterFiles.append(obj)

        tet
        return filterFiles
    except Exception as e:
        raise Exception(f"list files in bucket error: {e}")


def upate_filename_path_with_repeat_index(absolute_path,filename,repeat_index) -> str:
    name, extension = filename.split(".")
    new_filename = f"{absolute_path}/{name}-{repeat_index}.{extension}"
    return new_filename

def return_process_filename_base_on_command_and_sort_filesize(
    first_n_files: str,
    bucket: str,
    default_files: list,
    s3_client: "botocore.client.S3",
    file_pattern: str,

) -> list:

    n_files = []
 

    files_dict = list_files_in_bucket(
        bucket_name=bucket, s3_client=s3_client, file_pattern=file_pattern
    )
    


    if first_n_files is None:
        # n_files = default_files
        if len(default_files) < 1:
            raise Exception ("first_n_files is None and  default files list is empty")
        else:
            n_files = default_files
            return n_files
        # return n_files
    else:
        try:
            if len(files_dict) == 0:
                raise Exception(f"No files matches in {bucket} bucket")

            if int(first_n_files) == 0:
                logging.info(f"Process all files in {bucket}")
                for file in files_dict:
                    n_files.append(file)
            else:
                logging.info(f"Process first {first_n_files} files")
                for file in files_dict[0 : int(first_n_files)]:
                    n_files.append(file)
                    # file_name = file['Key']
                    # match_file = glob.glob(file_globbing_key)
                    # print(f"---match_file :{match_file}")
                    # split_tup = os.path.splitext(file_name)
                    # file_extension = split_tup[1]
                    # if file_extension == file_type:
                    #     n_files.append(file)
        except Exception as e:
            logging.error(f"Input {first_n_files} is not an integer")
            raise e

        logging.info(f"len :{len(n_files)}")
        # print("------------")
        _temp_sorted_file_list = sorted(n_files, key=lambda k: k['Size'],reverse=True)

        sorted_files = [d['Key'] for d in _temp_sorted_file_list]

        return sorted_files


def update_image_tags_for_ecr(
    service_name: int = 1,
    ecr_repo: str = None,
) -> List[str]:
    """
    Update worker and server's image_name and tag aws.

    """
    image_name = f"{ecr_repo}/{service_name}"
    
    return image_name 




def send_command_to_server(
    read_server_list: list = [],
    files_list_in_namespace: list =[],
    sqs_url:str = None,
    aws_access_key :str = None,            
    aws_secret_access_key:str = None,
    aws_region:str = None,
    repeat_number_per_round: int = 1,
    file_pattern:str = None,
    data_bucket:str = None,
    process_column_keywords: list = [],
    solver: dict = {},
    user_id : str = None,

) -> List[str]:

    for index, server_dict in enumerate(read_server_list):
        print(f"index :{index}")
        if not 'name' in server_dict or not 'namespace' in server_dict:
            raise ValueError("name or namespace key does not exists")
        
        server_name = server_dict['name']
        namespace = server_dict['namespace']

        logging.info(f"Invoke server: {server_name} in namespace: {namespace}")
        if namespace not in files_list_in_namespace:
            raise Exception(f"cannot find {namespace} in  {files_list_in_namespace}")
        process_file_lists = files_list_in_namespace[namespace]
        
        config_str= create_config_parameters_to_app(
            po_server_name=server_name,
            files_list=process_file_lists,
            sqs_url = sqs_url,
            aws_access_key= aws_access_key,
            aws_secret_access_key = aws_secret_access_key,
            aws_region = aws_region,
            repeat_number_per_round = repeat_number_per_round,
            file_pattern = file_pattern,
            data_bucket = data_bucket,
            process_column_keywords = process_column_keywords,
            solver = solver,
            user_id = user_id
        )
        # logging.info(f"config_str: {config_str}")

        resp = invoke_exec_k8s_run_process_files(
            config_params_str=config_str,
            pod_name=server_name,
            namespace = namespace,
        )
        logging.info(f"invoke k8s resp:{resp}")
        print(f"namespace:{namespace} server_name:{server_name} resp: {resp} ")
    return None

def create_config_parameters_to_app(
    po_server_name:str = None,
    files_list : list = [],
    sqs_url :str = None,
    aws_access_key: str = None,
    aws_secret_access_key :str = None,
    aws_region :str = None,
    repeat_number_per_round :int = 1,
    file_pattern:str = None,
    data_bucket:str = None,
    process_column_keywords: str = None,
    solver: dict = {},
    user_id : str = None,

) -> str:

    config_dict = {}
    try:
        config_dict["default_process_files"] = json.dumps(files_list)
        config_dict['po_server_name'] = po_server_name
        config_dict['sqs_url'] = sqs_url
        config_dict['aws_access_key'] = aws_access_key
        config_dict['aws_secret_access_key'] = aws_secret_access_key
        config_dict['aws_region'] = aws_region
        config_dict['repeat_number_per_round'] = repeat_number_per_round
        config_dict['file_pattern'] = file_pattern
        config_dict['data_bucket'] = data_bucket
        config_dict['process_column_keywords'] = process_column_keywords
        config_dict['solver'] = solver
        config_dict['user_id'] = user_id
        config_str = json.dumps(config_dict)
        logging.info(config_str)
    except ValueError as e:
        raise ValueError(f"pase config parametes failed {e}")
    return config_str


# def check_file_extension(
#     files_list:list,
#     extension:
# )

# def get_file_path_based_on_env(file_name, env, file_path_local, file_path_cloud, repeat_index, user_id):
#     """ return full saved file name and path based on env"""
#     file_path_name = ""
#     # add repeat_index into filename
#     # _relative_path, filename = os.path.split(file_name)
#     # print(_relative_path, filename)
#     name, extension = file_name.split(".")
   
#     new_filename = f"{name}-{repeat_index}.{extension}"
#     if env == Environments.AWS.name:
#         file_path_name = file_path_cloud +"/" + user_id + "/" + new_filename

#     else:
#         # check if directory exist 
#         base_path = os.getcwd()
#         local_full_path = f"{base_path}/{file_path_local}"
#         if not os.path.exists(local_full_path):
#             logging.info(f"{local_full_path} does not exist. Create {local_full_path}")
#             os.mkdir(local_full_path)
#         file_path_name = file_path_local +"/" + new_filename
        
#     return file_path_name   

def upload_file_to_s3(
    bucket: str = None,
    source_file_local: str = None,
    target_file_s3: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:

    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    response = s3_client.upload_file(source_file_local, bucket, target_file_s3)
    logging.info(f"Upload {source_file_local} success")
