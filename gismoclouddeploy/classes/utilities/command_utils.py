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
def checck_server_ready_and_get_name(
    sever_name: str = None,
    is_docker: bool = False,
    namespace:str = "default"
) -> str:
    server_name = ""
    if is_docker:

        server_name = sever_name
        
    else:
        wait_time = 40
        delay = 5
        # number_server = sever_name
        # print(f"number_server : {number_server}")
        while wait_time > 0:

            logger.info(f"K8s reboot Wait {wait_time} sec")
            time.sleep(delay)
            wait_time -= delay
        # server_name = get_k8s_deployment(prefix="server")
        # server_name = get_k8s_pod_name(pod_name="server")
        server_name_list =  get_k8s_pod_name_list(pod_name="server", number_server=1)
        logger.info(f"server_name_list ====> {server_name_list}")

        # ping server and check status
        if len(server_name_list) == 0:
            raise Exception("Find k8s pod server error")


        return server_name_list

    return server_name



def start_process_command_to_server(
    server_list: list = None,
    worker_config_json: str = None,
    is_docker: bool = False,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    sqs_url: str = None,
) -> List[str]:
    worker_config_json["aws_access_key"] = aws_access_key
    worker_config_json["aws_secret_access_key"] = aws_secret_access_key
    worker_config_json["aws_region"] = aws_region
    worker_config_json["sqs_url"] = sqs_url

    for index, server_info in enumerate(server_list):
        server_name = server_info['name']
        namespace = server_info['namespace']

        logger.info(f"Invoke server: {server_name} in namespace: {namespace}")

        _files_list = worker_config_json['num_files_per_server_list'][index]
        worker_config_json["default_process_files"] = json.dumps(_files_list)
        worker_config_json["po_server_name"] = server_name
        worker_config_str = json.dumps(worker_config_json)
        resp = invoke_process_files_to_server_namespace(
            is_docker= is_docker,
            server_name=server_name,
            worker_config_str = worker_config_str,
            namespace = namespace,
        )
        # print(f"namespace:{namespace} server_name:{server_name} resp: {resp} ")
    return None


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

        # _resp = invoke_exec_k8s_run_process_files(
        #     config_params_str=worker_config_str,
        #     pod_name=server_name,
        #     first_n_files=None,
        #     namesapce = namespace,
        # )
    return _resp

def invoke_process_files_to_server(
    is_docker: bool = False,
    server_name: str = None,
    worker_config_str: str = None,
    number: int = None,
    namesapce: str = "default"
) -> str:
    print(namesapce)
    # if is_docker:
    #     _resp = invoke_exec_docker_run_process_files(
    #         config_params_str=worker_config_str,
    #         image_name=server_name,
    #         first_n_files=number,
    #         namesapce = namesapce,
    #     )
    # else:
    #     _resp = invoke_exec_k8s_run_process_files(
    #         config_params_str=worker_config_str,
    #         pod_name=server_name,
    #         first_n_files=number,
    #         namesapce = namesapce,
    #     )
    # return _resp


def print_dlq(
    delete_messages: bool,
    aws_key: str,
    aws_secret_key: str,
    aws_region: str,
    dlq_url: str,
    wait_time: int = 60,
    delay: float = 0.5,
) -> None:

    try:
        logger.info("Read DLQ")
        sqs_client = aws_utils.connect_aws_client(
            client_name="sqs",
            key_id=aws_key,
            secret=aws_secret_key,
            region=aws_region,
        )
    except Exception as e:
        raise e

    while wait_time:
        messages = receive_queue_message(
            queue_url=dlq_url,
            MaxNumberOfMessages=10,
            sqs_client=sqs_client,
            wait_time=1,
        )
        if "Messages" in messages:
            for msg in messages["Messages"]:
                msg_body = msg["Body"]
                receipt_handle = msg["ReceiptHandle"]
                logger.info(f"The message body:\n {msg_body}")

                # logger.info('Deleting message from the queue...')
                if delete_messages:
                    delete_queue_message(dlq_url, receipt_handle, sqs_client)

                # logger.info(f"Received and deleted message(s) from {dlq_url}.")
                # print(receipt_handle)
        else:
            logger.info("Clean DLQ message completed")
            return

        wait_time -= 1
        time.sleep(delay)



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



def update_config_json_image_name_and_tag_base_on_env(
    number_of_server: int = 1,
    number_of_queue: int = 1,
    is_local: bool = False,
    is_docker: bool = False,
    image_tag: str = None,
    ecr_repo: str = None,
    ecr_client=None,
    services_config_list: List[str] = None,
    is_celeryflower_on: bool = False
) -> List[str]:
    """
    Update worker and server's image_name and tag based on local or aws.

    """

    for service in services_config_list:
        # only inspect worker and server
        # if service == "server":
        #     services_config_list[service]['desired_replicas'] = number_of_server
        # if service == "rabbitmq" or service == "redis":
        #     services_config_list[service]['desired_replicas'] = number_of_queue
        if service == "worker" or service == "server" or service =="celeryflower":
            if service =="celeryflower" and is_celeryflower_on is False:
                logger.info("Skip celery flower service")
                continue
            
            if is_local:
                imagePullPolicy = "IfNotPresent"
                logger.info(f"update {service} config in local")
                # update image policy
                services_config_list[service]["imagePullPolicy"] = imagePullPolicy
            else:

                if is_docker:
                    imagePullPolicy = "IfNotPresent"
                    logger.info(f"update {service} config in local")
                    # update image policy
                    services_config_list[service]["imagePullPolicy"] = imagePullPolicy
                else:
                    imagePullPolicy = "Always"
                    logger.info(f"update {service} image on AWS")
                    image_base_url = f"{ecr_repo}/{service}"
                    services_config_list[service]["image_name"] = image_base_url

            # Updated image tag
            services_config_list[service]["image_tag"] = image_tag

    return services_config_list

    # if is_local is False:


def download_file_from_s3(
    bucket_name: str = None,
    source_file: str = None,
    target_file: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
):
    try:
        s3_client = aws_utils.connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
        # Download the file from S3
        s3_client.download_file(bucket_name, source_file, target_file)
        return
    except Exception as e:
        raise Exception(f"Download file failed{e}")


def delete_all_files_in_foler_of_a_bucket(
    bucket_name: str = None,
    source_folder: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:

    if (
        bucket_name is None
        or source_folder is None
        or aws_access_key is None
        or aws_secret_access_key is None
        or aws_region is None
    ):
        raise Exception("Input is None")

    s3_client = aws_utils.connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    try:
        filter_files = list_files_in_folder_of_bucket(
            bucket_name, source_folder, s3_client
        )
        if len(filter_files) == 0:
            logger.info("no files in source folder")
            return
    except Exception:
        logger.info("No source folder")
        return
    try:
        for file in filter_files:
            delete_files_from_bucket(bucket_name, file, s3_client)
    except Exception as e:
        logger.error(f"delete files in {source_folder} failed ---> {e}")
        raise e


def list_files_in_folder_of_bucket(
    bucket_name: str, file_path: str, s3_client: "botocore.client.S3"
) -> List[str]:
    """Get filename from a folder of the bucket , remove non csv file"""

    response = s3_client.list_objects_v2(Bucket=bucket_name)
    files = response["Contents"]
    filterFiles = []
    for file in files:
        split_tup = os.path.splitext(file["Key"])
        path, filename = os.path.split(file["Key"])
        file_extension = split_tup[1]
        if file_extension == ".csv" and path == file_path:
            filterFiles.append(file["Key"])
    return filterFiles


def delete_files_from_bucket(
    bucket_name: str, full_path: str, s3_client: "botocore.client.S3"
) -> None:
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=full_path)
        print(f"Deleted {full_path} success!!")
    except Exception as e:
        print(f"Delete file error ---> {e}")
        raise e


def check_solver_and_upload(
    ecr_repo: str = None,
    solver_name: str = None,
    saved_solver_bucket: str = None,
    solver_lic_file_name: str = None,
    solver_lic_local_path: str = None,
    saved_temp_path_in_bucket: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:
    if (
        solver_name is None
        or saved_solver_bucket is None
        or solver_lic_file_name is None
        or solver_lic_local_path is None
        or saved_temp_path_in_bucket is None
        or aws_access_key is None
        or aws_secret_access_key is None
        or aws_region is None
    ):
        logger.info("Solver info is None")
        return

    # check local solver lic
    local_solver_file = solver_lic_local_path + "/" + solver_lic_file_name
    if exists(local_solver_file) is False:
        logger.warning("Local solver lic does not exist")
        raise Exception("Solver lic does not exist")

    # upload solver
    try:
        logger.info("Upload solver success")
        s3_client = aws_utils.connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
        target_file_path_name = saved_temp_path_in_bucket + "/" + solver_lic_file_name
        response = s3_client.upload_file(
            local_solver_file, saved_solver_bucket, target_file_path_name
        )
        logger.info("Upload solver success")
    except ClientError as e:
        logger.error(f"Update solver failed {e}")
        raise e
    logger.info(
        f"Upload sover to {saved_solver_bucket}::{target_file_path_name} success"
    )
    return


def check_and_wait_server_ready(
    is_docer: bool = False, server_name: str = None, counter: int = 2, delay: int = 1
) -> bool:
    while counter > 0:
        task_id = ""
        # ping server
        try:
            if is_docer:
                task_id = invoke_exec_docker_ping_worker(service_name=server_name)
            else:
                task_id = invoke_exec_k8s_ping_worker(service_name=server_name)
            if len(task_id) > 0:
                (f"Ping {server_name} Success ")
                break
        except:
            logger.info(f"Ping {server_name} failed, retry!!!")

        counter -= delay
        time.sleep(delay)
        if counter <= 0:
            logger.error(f"Ping {server_name} over time")
            return

    while counter > 0:

        result = ""
        if is_docer:
            result = invoke_exec_docker_check_task_status(
                server_name=server_name, task_id=str(task_id).strip("\n")
            )
        else:
            logger.info("Chcek k8s worker status")
            result = invoke_exec_k8s_check_task_status(
                server_name=server_name, task_id=str(task_id).strip("\n")
            )
        logger.info(result)
        # conver json to
        res_json = {}
        dataform = str(result).strip("'<>() ").replace("'", '"').strip("\n")

        try:
            res_json = json.loads(dataform)
            status = res_json["task_status"]
            # logger.info(f" ==== Check {server_name} Status: {res_json}====")
            if status == "SUCCESS":
                return True
        except Exception as e:
            logger.info(f"load json failed res:{result} {e}")
            return False

        counter -= delay
        time.sleep(delay)
    logger.error("check server reday orvertime")
    return False


def convert_yaml_to_json(yaml_file: str = None):
    try:
        with open(yaml_file, "r") as stream:
            config_json = yaml.safe_load(stream)
        return config_json
    except IOError as e:
        raise f"I/O error:{e}"


def verify_keys_in_configfile(config_dict:dict):
    try:
        assert 'data_bucket' in config_dict
        assert 'file_pattern' in config_dict
        assert 'process_column_keywords' in config_dict
        assert 'saved_bucket' in config_dict


    except AssertionError as e:
        raise AssertionError(f"Assert configfile error {e}")