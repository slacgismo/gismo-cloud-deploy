from curses import flash
from http import server
from os.path import exists
from re import I
import botocore

from typing import List
import yaml
import json
from botocore.exceptions import ClientError

from .k8s_utils import (
    get_k8s_image_and_tag_from_deployment,
    create_k8s_deployment_from_yaml,
    get_k8s_pod_name,
    # get_k8s_pod_name_list,
)

from .invoke_function import (
    invoke_kubectl_delete_deployment,
    invoke_exec_docker_run_process_files,
    invoke_exec_k8s_run_process_files,
    invoke_exec_k8s_ping_worker,
    invoke_exec_docker_check_task_status,
    invoke_exec_docker_ping_worker,
    invoke_exec_k8s_check_task_status,
)
from gismoclouddeploy.server.utils import aws_utils
# from server.utils import aws_utils
import time
from .sqs import (
    receive_queue_message,
    delete_queue_message,
)

import os

from typing import Union
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

def invoke_process_files_to_server_namespace(
    is_docker: bool = False,
    server_name: str = None,
    worker_config_str: str = None,
    namespace: str = "default"
) ->str:
    if is_docker:
        _resp = invoke_exec_docker_run_process_files(
            config_params_str=worker_config_str,
            image_name=server_name,
            first_n_files=None,
            namesapce = namespace,
        )
    else:
        _resp = invoke_exec_k8s_run_process_files(
            config_params_str=worker_config_str,
            pod_name=server_name,
            first_n_files=None,
            namespace = namespace,
        )

    return _resp


def create_or_update_k8s_deployment(
    service_name: str = None,
    image_base_url: str = None,
    image_tag: str = None,
    imagePullPolicy: str = "Always",
    desired_replicas: int = 1,
    k8s_file_name: str = None,
    # rollout: bool = False,
    namespace:str = "default"
):

    try:
        curr_image, curr_tag, curr_status = get_k8s_image_and_tag_from_deployment(
            prefix=service_name,
            namespace = namespace
        )
        # print(curr_image,curr_tag, curr_status )
        image_url = f"{image_base_url}:{image_tag}"
        if curr_status is None:
            # Deployment does not exist

            logger.info(
                f"Deployment {image_url} does not exist "
            )
            logger.info(f" Create {image_url} deployment  namespace: {namespace}")
            create_k8s_deployment_from_yaml(
                service_name=service_name,
                image_url_tag=image_url,
                imagePullPolicy=imagePullPolicy,
                desired_replicas=desired_replicas,
                file_name=k8s_file_name,
                namspace=namespace,
            )
        else:
            logger.info(
                f"Deployment {service_name}:{curr_tag} exist"
            )

            if (
                curr_status.unavailable_replicas is not None
                or curr_tag != image_tag
                or int(curr_status.replicas) != int(desired_replicas)
            ):

                if curr_status.unavailable_replicas is not None:
                    logger.info("Deployment status error")
                if int(curr_status.replicas) != int(desired_replicas):
                    logger.info(
                        f"Update replicas from:{curr_status.replicas} to {desired_replicas}"
                    )
                if curr_tag != image_tag:
                    logger.info(
                        f"Update from {service_name}:{curr_tag} to {service_name}:{image_tag}"
                    )

                logger.info(f"Delete  {service_name}:{curr_tag} ")
                output = invoke_kubectl_delete_deployment(name=service_name)
                # logger.info(output)

                # re-create deplpoyment

                create_k8s_deployment_from_yaml(
                    service_name=service_name,
                    image_url_tag=image_url,
                    imagePullPolicy=imagePullPolicy,
                    desired_replicas=desired_replicas,
                    file_name=k8s_file_name,
                )
    except Exception as e:
        logger.info(e)
        raise e

def delete_files_from_bucket(
    bucket_name: str, full_path: str, s3_client: "botocore.client.S3"
) -> None:
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=full_path)
        print(f"Deleted {full_path} success!!")
    except Exception as e:
        print(f"Delete file error ---> {e}")
        raise e



# def convert_yaml_to_json(yaml_file: str = None):
#     try:
#         with open(yaml_file, "r") as stream:
#             config_json = yaml.safe_load(stream)
#         return config_json
#     except IOError as e:
#         raise f"I/O error:{e}"


def verify_keys_in_configfile(config_dict:dict):
    try:
        assert 'data_bucket' in config_dict
        assert 'file_pattern' in config_dict
        assert 'process_column_keywords' in config_dict
        assert 'saved_bucket' in config_dict


    except AssertionError as e:
        raise AssertionError(f"Assert configfile error {e}")