from .check_aws import check_aws_validity, check_environment_is_aws
from os.path import exists
import logging
import yaml
import os
import socket
from .invoke_function import invoke_eks_get_cluster
import re
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)
from typing import List
import math

def modiy_config_parameters(
    configfile: str = "config.yaml",
    nodesscale: int = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    sqs_url: str = None,
    sns_topic: str = None,
    dlq_url: str = None,
    ecr_repo: str = None,
    current_repeat_number:int= 0,
    s3_client = None,
    first_n_files:int = 0 
) -> str:

    try:
        check_aws_validity(key_id=aws_access_key, secret=aws_secret_access_key)
    except Exception as e:
        logger.error(f"AWS credential failed: {e}")
        return

    # check config exist
    config_yaml = f"./config/{configfile}"

    if exists(config_yaml) is False:
        logger.warning(
            f"./config/{configfile} not exist, use default config.yaml instead"
        )
        config_yaml = f"./config/config.yaml"

    """
    Generated unique file name and folder to save data, logs, solver's lic and plot
    """

    config_json = convert_yaml_to_json(yaml_file=config_yaml)
    host_name = (socket.gethostname())
    user_id = re.sub('[^a-zA-Z0-9]', '', host_name)
    print(f"----- user_id :{user_id}")
    config_json["worker_config"]["user_id"] = user_id
    config_json["worker_config"]["solver"]["saved_temp_path_in_bucket"] = (
        config_json["worker_config"]["solver"]["saved_temp_path_in_bucket"]
        + "/"
        + user_id
    )
    config_json["worker_config"]["saved_rumtime_image_name"] = f"gantt-{user_id}-{current_repeat_number}.png"
    config_json["worker_config"][
        "saved_performance_file"
    ] = f"performance-{user_id}-{current_repeat_number}.txt"
    config_json["worker_config"]["saved_data_target_filename"] = f"data-{user_id}-{current_repeat_number}.csv"
    config_json["worker_config"]["saved_logs_target_filename"] = f"logs-{user_id}-{current_repeat_number}.csv"
    config_json["worker_config"]["saved_error_target_filename"] = f"error-{user_id}-{current_repeat_number}.csv"

    # check if local path exist
    result_local_folder = config_json["worker_config"]["saved_path_local"]
    if os.path.isdir(result_local_folder) is False:
        logger.info(f"Create local {result_local_folder} path")
        os.mkdir(result_local_folder)

    # Generate local results files name

    config_json["worker_config"]["save_data_file_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_data_target_filename"]
    )

    config_json["worker_config"]["save_logs_file_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_logs_target_filename"]
    )

    config_json["worker_config"]["save_error_file_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_error_target_filename"]
    )

    config_json["worker_config"]["save_plot_file_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_rumtime_image_name"]
    )

    config_json["worker_config"]["save_performance_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_performance_file"]
    )

    # Generate AWS results files name

    config_json["worker_config"]["save_data_file_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_data_target_filename"]
    )

    config_json["worker_config"]["save_logs_file_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_logs_target_filename"]
    )

    config_json["worker_config"]["save_error_file_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_error_target_filename"]
    )

    config_json["worker_config"]["save_plot_file_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_rumtime_image_name"]
    )

    config_json["worker_config"]["save_performance_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_performance_file"]
    )

    # Update  eks cluster name and groupname
    if nodesscale is not None and check_environment_is_aws():
        logger.info(f"Update nodes eks and worker replicas to{nodesscale}")
        config_json["aws_config"]["eks_nodes_number"] = int(nodesscale)
        config_json["services_config_list"]["worker"]["desired_replicas"] = int(
            nodesscale
        )
    if check_environment_is_aws():
        logger.info("====== Runing on AWS ========= ")
        cluster_file = config_json["aws_config"]["cluster_file"]
        cluster_file_json = convert_yaml_to_json(yaml_file=cluster_file)
        cluster_name = cluster_file_json["metadata"]["name"]
        nodegroup_name = cluster_file_json["nodeGroups"][0]["name"]
        instanceType = cluster_file_json["nodeGroups"][0]["instanceType"]
        max_nodes_num = cluster_file_json["nodeGroups"][0]["maxSize"]
        
        tags = cluster_file_json["nodeGroups"][0]["tags"]
        config_json["aws_config"]["cluster_name"] = cluster_name
        config_json["aws_config"]["nodegroup_name"] = nodegroup_name
        config_json["aws_config"]["aws_access_key"] = aws_access_key
        config_json["aws_config"]["instanceType"] = instanceType
        

        current_clust_name = invoke_eks_get_cluster()
        print(current_clust_name)
    else:
        logger.info("====== Runing on Local ========= ")
        
    config_json["aws_config"]["aws_access_key"] = aws_access_key
    config_json["aws_config"]["aws_secret_access_key"] = aws_secret_access_key
    config_json["aws_config"]["aws_region"] = aws_region
    config_json["aws_config"]["sns_topic"] = sns_topic
    config_json["aws_config"]["sqs_url"] = sqs_url
    config_json["aws_config"]["dlq_url"] = dlq_url
    config_json["aws_config"]["ecr_repo"] = ecr_repo



    n_files = return_process_filename_base_on_command_and_sort_filesize(
        first_n_files=first_n_files,
        bucket=config_json["worker_config"]["data_bucket"],
        default_files=config_json["worker_config"]["default_process_files"],
        s3_client=s3_client,
        file_format=config_json["worker_config"]["data_file_type"],
        file_type=config_json["worker_config"]['data_file_type']
    )
    total_number_files = len(n_files)
    print(total_number_files)
    number_worker_nodes = 1
    if check_environment_is_aws():
        number_worker_nodes = int(config_json["aws_config"]["eks_nodes_number"])
    num_worker_pods_per_server = int(config_json["worker_config"]["num_worker_pods_per_server"])
    number_of_server = math.ceil( number_worker_nodes / num_worker_pods_per_server )
    num_files_per_server =  math.ceil(total_number_files/number_of_server)
    
    # update desired_replicas of server , rabbitmq and redis
    # config_json['services_config_list']['worker']['desired_replicas'] = 
    config_json['services_config_list']['server']['desired_replicas'] = number_of_server
    # config_json['services_config_list']['redis']['desired_replicas'] = number_of_server
    config_json['services_config_list']['rabbitmq']['desired_replicas'] = number_of_server
        
        
    # num_files_per_server = int(config_json["worker_config"]["num_files_per_server"])
    start_index = 0 
    end_inedx = num_files_per_server
    
    if number_of_server < 1 :
        number_of_server = 1
    number_of_queue = number_of_server
    # _new_nodes = int(nodesscale) + math.ceil( (number_of_server)*3/2)
    if nodesscale is not None:
        _worker_replicas = (int(nodesscale)  - (math.ceil( (number_of_server)*2/2) + 1))*2
        if _worker_replicas < 1:
            _worker_replicas = 1
        # udpate eks nodes number
        config_json['services_config_list']['worker']['desired_replicas'] = _worker_replicas
        config_json["aws_config"]["eks_nodes_number"] = nodesscale
    
    process_files_per_server_list = []

    while start_index < len(n_files):
        _files = n_files[start_index : end_inedx]
        process_files_per_server_list.append(_files)
        start_index = end_inedx
        end_inedx += num_files_per_server


    # update  files list of server
    
    config_json["worker_config"]['num_files_per_server_list'] = process_files_per_server_list

    
    return config_json


def convert_yaml_to_json(yaml_file: str = None):
    try:
        with open(yaml_file, "r") as stream:
            config_json = yaml.safe_load(stream)
        return config_json
    except IOError as e:
        raise f"I/O error:{e}"



def list_files_in_bucket(bucket_name: str, s3_client, file_format: str):
    """Get filename and size from S3 , remove non csv file"""
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    files = response["Contents"]
    filterFiles = []
    for file in files:
        split_tup = os.path.splitext(file["Key"])
        file_extension = split_tup[1]
        if file_extension == file_format:
            obj = {
                "Key": file["Key"],
                "Size": file["Size"],
            }
            filterFiles.append(obj)
    return filterFiles

def return_process_filename_base_on_command_and_sort_filesize(
    first_n_files: str,
    bucket: str,
    default_files: List[str],
    s3_client: "botocore.client.S3",
    file_format: str,
    file_type: str 
) -> List[str]:

    n_files = []
    files_dict = list_files_in_bucket(
        bucket_name=bucket, s3_client=s3_client, file_format=file_format
    )

    if first_n_files is None:
        n_files = default_files
        return n_files
    else:
        try:
            if int(first_n_files) == 0:
                logger.info(f"Process all files in {bucket}")
                for file in files_dict:
                    n_files.append(file)
            else:
                logger.info(f"Process first {first_n_files} files")
                for file in files_dict[0 : int(first_n_files)]:
                    file_name = file['Key']
                    split_tup = os.path.splitext(file_name)
                    file_extension = split_tup[1]
                    if file_extension == file_type:
                        n_files.append(file)
        except Exception as e:
            logger.error(f"Input {first_n_files} is not an integer")
            raise e

    print(f"len :{len(n_files)}")
    # print("------------")
    _temp_sorted_file_list = sorted(n_files, key=lambda k: k['Size'],reverse=True)

    sorted_files = [d['Key'] for d in _temp_sorted_file_list]

    return sorted_files