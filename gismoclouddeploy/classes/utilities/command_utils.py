from re import I
import botocore
import fnmatch
import time
from .k8s_utils import (
    get_k8s_image_and_tag_from_deployment,
    create_k8s_deployment_from_yaml,
)

from .invoke_function import (
    invoke_kubectl_delete_deployment,
    invoke_exec_k8s_run_process_files,
)

import logging
from typing import List
import json
from mypy_boto3_s3.client import S3Client


def create_or_update_k8s_deployment(
    service_name: str = None,
    image_base_url: str = None,
    image_tag: str = None,
    imagePullPolicy: str = "Always",
    desired_replicas: int = 1,
    k8s_file_name: str = None,
    # rollout: bool = False,
    namespace: str = "default",
):

    try:
        curr_image, curr_tag, curr_status = get_k8s_image_and_tag_from_deployment(
            prefix=service_name, namespace=namespace
        )
        # print(curr_image,curr_tag, curr_status )
        image_url = f"{image_base_url}:{image_tag}"
        if curr_status is None:
            # Deployment does not exist

            logging.info(f"Deployment {image_url} does not exist ")
            logging.info(f" Create {image_url} deployment  namespace: {namespace}")
            create_k8s_deployment_from_yaml(
                service_name=service_name,
                image_url_tag=image_url,
                imagePullPolicy=imagePullPolicy,
                desired_replicas=desired_replicas,
                file_name=k8s_file_name,
                namspace=namespace,
            )
        else:
            logging.info(f"Deployment {service_name}:{curr_tag} exist")

            if (
                curr_status.unavailable_replicas is not None
                or curr_tag != image_tag
                or int(curr_status.replicas) != int(desired_replicas)
            ):

                if curr_status.unavailable_replicas is not None:
                    logging.info("Deployment status error")
                if int(curr_status.replicas) != int(desired_replicas):
                    logging.info(
                        f"Update replicas from:{curr_status.replicas} to {desired_replicas}"
                    )
                if curr_tag != image_tag:
                    logging.info(
                        f"Update from {service_name}:{curr_tag} to {service_name}:{image_tag}"
                    )

                logging.info(f"Delete  {service_name}:{curr_tag} ")
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
        logging.info(e)
        raise e


def verify_keys_in_configfile(config_dict: dict):
    try:
        verify_a_key_in_dict(dict_format=config_dict, key="scale_eks_nodes_wait_time")
        verify_a_key_in_dict(dict_format=config_dict, key="interval_of_wait_pod_ready")
        verify_a_key_in_dict(dict_format=config_dict, key="data_bucket")
        verify_a_key_in_dict(dict_format=config_dict, key="file_pattern")
        verify_a_key_in_dict(dict_format=config_dict, key="process_column_keywords")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_bucket")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_path_cloud")
        verify_a_key_in_dict(dict_format=config_dict, key="acccepted_idle_time")
        verify_a_key_in_dict(dict_format=config_dict, key="interval_of_checking_sqs")
        verify_a_key_in_dict(dict_format=config_dict, key="filename")
        verify_a_key_in_dict(dict_format=config_dict, key="repeat_number_per_round")
        verify_a_key_in_dict(dict_format=config_dict, key="is_celeryflower_on")
        # Solver
        verify_a_key_in_dict(dict_format=config_dict, key="solver_name")
        verify_a_key_in_dict(
            dict_format=config_dict, key="solver_lic_target_path_in_images_dest"
        )
        verify_a_key_in_dict(
            dict_format=config_dict, key="solver_lic_file_local_source"
        )
        logging.info("Verify config key success")
    except Exception as e:
        raise Exception(f"Assert error {e}")


def verify_a_key_in_dict(dict_format: dict, key: str) -> None:
    try:
        assert key in dict_format
    except Exception:
        raise Exception(f"does not contain {key}")


def do_nothing_and_wait(wait_time: int = 60, delay: int = 3):

    while wait_time > 0:
        time.sleep(delay)
        wait_time -= delay
        logging.info(f"Waiting.. {wait_time} sec")
    return


def create_config_parameters_to_app(
    po_server_name: str = None,
    files_list: list = [],
    sqs_url: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    repeat_number_per_round: int = 1,
    file_pattern: str = None,
    data_bucket: str = None,
    process_column_keywords: str = None,
    solver: dict = {},
    user_id: str = None,
) -> str:

    config_dict = {}
    try:
        config_dict["default_process_files"] = json.dumps(files_list)
        config_dict["po_server_name"] = po_server_name
        config_dict["sqs_url"] = sqs_url
        config_dict["aws_access_key"] = aws_access_key
        config_dict["aws_secret_access_key"] = aws_secret_access_key
        config_dict["aws_region"] = aws_region
        config_dict["repeat_number_per_round"] = repeat_number_per_round
        config_dict["file_pattern"] = file_pattern
        config_dict["data_bucket"] = data_bucket
        config_dict["process_column_keywords"] = process_column_keywords
        config_dict["solver"] = solver
        config_dict["user_id"] = user_id
        config_str = json.dumps(config_dict)

    except ValueError as e:
        raise ValueError(f"pase config parametes failed {e}")
    return config_str


def send_command_to_server(
    read_server_list: list = [],
    files_list_in_namespace: list = [],
    sqs_url: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    repeat_number_per_round: int = 1,
    file_pattern: str = None,
    data_bucket: str = None,
    process_column_keywords: list = [],
    solver: dict = {},
    user_id: str = None,
) -> List[str]:

    for index, server_dict in enumerate(read_server_list):
        # print(f"index :{index}")
        if not "name" in server_dict or not "namespace" in server_dict:
            raise ValueError("name or namespace key does not exists")

        server_name = server_dict["name"]
        namespace = server_dict["namespace"]

        logging.info(f"Invoke server: {server_name} in namespace: {namespace}")
        if namespace not in files_list_in_namespace:
            raise Exception(f"cannot find {namespace} in  {files_list_in_namespace}")
        process_file_lists = files_list_in_namespace[namespace]

        config_str = create_config_parameters_to_app(
            po_server_name=server_name,
            files_list=process_file_lists,
            sqs_url=sqs_url,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            repeat_number_per_round=repeat_number_per_round,
            file_pattern=file_pattern,
            data_bucket=data_bucket,
            process_column_keywords=process_column_keywords,
            solver=solver,
            user_id=user_id,
        )
        # logging.info(f"config_str: {config_str}")

        resp = invoke_exec_k8s_run_process_files(
            config_params_str=config_str,
            pod_name=server_name,
            namespace=namespace,
        )
        # logging.info(f"invoke k8s resp:{resp}")
        # print(f"namespace:{namespace} server_name:{server_name} resp: {resp} ")
    return None


def upate_filename_path_with_repeat_index(absolute_path, filename, repeat_index) -> str:
    name, extension = filename.split(".")
    new_filename = f"{absolute_path}/{name}-{repeat_index}.{extension}"
    return new_filename


def return_process_filename_base_on_command_and_sort_filesize(
    first_n_files: str,
    bucket: str,
    default_files: list,
    s3_client: S3Client,
    file_pattern: str,
) -> list:

    n_files = []

    files_dict = list_files_in_bucket(
        bucket_name=bucket, s3_client=s3_client, file_pattern=file_pattern
    )

    if first_n_files is None:
        # n_files = default_files
        if len(default_files) < 1:
            raise Exception("first_n_files is None and  default files list is empty")
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
        except Exception as e:
            logging.error(f"Input {first_n_files} is not an integer")
            raise e

        logging.info(f"len :{len(n_files)}")
        # print("------------")
        _temp_sorted_file_list = sorted(n_files, key=lambda k: k["Size"], reverse=True)

        sorted_files = [d["Key"] for d in _temp_sorted_file_list]

        return sorted_files


def list_files_in_bucket(bucket_name: str, s3_client, file_pattern: str):
    """Get filename and size from S3 , fillter file format file"""
    try:

        response = s3_client.list_objects_v2(Bucket=bucket_name)
        files = response["Contents"]
        filterFiles = []
        tet = []
        for file in files:
            filename = file["Key"]

            matches = fnmatch.fnmatch(filename, file_pattern)
            print(f"matches :{matches}")
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
