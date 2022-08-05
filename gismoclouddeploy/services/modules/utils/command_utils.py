from os.path import exists
import botocore

from typing import List
import yaml
import json
from botocore.exceptions import ClientError

from .k8s_utils import (
    get_k8s_image_and_tag_from_deployment,
    create_k8s_deployment_from_yaml,
    get_k8s_pod_name,
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

from server.utils import aws_utils
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
    deployment_services_list: List[str] = None,
    is_docker: bool = False,
) -> str:
    server_name = ""
    if is_docker:

        server_name = deployment_services_list["server"]["image_name"]
    else:
        wait_time = 15
        delay = 5
        while wait_time > 0:

            logger.info(f"K8s reboot Wait {wait_time} sec")
            time.sleep(delay)
            wait_time -= delay
        # server_name = get_k8s_deployment(prefix="server")
        server_name = get_k8s_pod_name(pod_name="server")

        logger.info(f"server name ====> {server_name}")

        if server_name is None:
            logger.error("Cannot find server pod")
            raise Exception("Find k8s pod server error")
    if (
        check_and_wait_server_ready(
            is_docer=is_docker, server_name=server_name, counter=2, delay=1
        )
        is not True
    ):
        logger.error("Wait server ready failed")
        raise Exception(f"Wait {server_name} failed")

    return server_name


def send_command_to_server(
    server_name: str = None,
    number: int = Union[int, None],
    worker_config_json: str = None,
    is_docker: bool = False,
    num_file_to_process_per_round: int = 10,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    sns_topic: str = None,
    sqs_url: str = None,
) -> List[str]:
    worker_config_json["aws_access_key"] = aws_access_key
    worker_config_json["aws_secret_access_key"] = aws_secret_access_key
    worker_config_json["aws_region"] = aws_region
    worker_config_json["sns_topic"] = sns_topic
    worker_config_json["sqs_url"] = sqs_url
    s3_client = aws_utils.connect_aws_client(
        client_name="s3",
        key_id=worker_config_json["aws_access_key"],
        secret=worker_config_json["aws_secret_access_key"],
        region=worker_config_json["aws_region"],
    )
    n_files = return_process_filename_base_on_command(
        first_n_files=number,
        bucket=worker_config_json["data_bucket"],
        default_files=worker_config_json["default_process_files"],
        s3_client=s3_client,
        file_format=worker_config_json["data_file_type"],
    )
    # print(len(n_files))
    # print(n_files)
    # start_index = 0
    # end_index = num_file_to_process_per_round
    # if end_index > len(n_files):
    #     end_index = len(n_files)

    total_tasks_ids = []
    # while start_index < len(n_files):
    process_files_list = []
    for file in n_files:
        process_files_list.append(file)
        # print(f"--------------{file}")
    #
    worker_config_json["default_process_files"] = json.dumps(process_files_list)
    worker_config_str = json.dumps(worker_config_json)
    # invoke process files
    resp = invoke_process_files_to_server(
        is_docker=is_docker,
        server_name=server_name,
        worker_config_str=worker_config_str,
        number=None,
    )

    return None


def return_process_filename_base_on_command(
    first_n_files: str,
    bucket: str,
    default_files: List[str],
    s3_client: "botocore.client.S3",
    file_format: str,
) -> List[str]:

    n_files = []
    files_dict = list_files_in_bucket(
        bucket_name=bucket, s3_client=s3_client, file_format=file_format
    )

    if first_n_files is None:
        n_files = default_files
    else:
        try:
            if int(first_n_files) == 0:
                logger.info(f"Process all files in {bucket}")
                for file in files_dict:
                    n_files.append(file["Key"])
            else:
                logger.info(f"Process first {first_n_files} files")
                for file in files_dict[0 : int(first_n_files)]:
                    n_files.append(file["Key"])
        except Exception as e:
            logger.error(f"Input {first_n_files} is not an integer")
            raise e
    return n_files


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


def invoke_process_files_to_server(
    is_docker: bool = False,
    server_name: str = None,
    worker_config_str: str = None,
    number: int = None,
) -> str:

    if is_docker:
        _resp = invoke_exec_docker_run_process_files(
            config_params_str=worker_config_str,
            image_name=server_name,
            first_n_files=number,
        )
    else:
        _resp = invoke_exec_k8s_run_process_files(
            config_params_str=worker_config_str,
            pod_name=server_name,
            first_n_files=number,
        )
    return _resp


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
    rollout: bool = False,
):
    try:
        curr_image, curr_tag, curr_status = get_k8s_image_and_tag_from_deployment(
            prefix=service_name
        )
        # print(curr_image,curr_tag, curr_status )
        image_url = f"{image_base_url}:{image_tag}"
        if curr_status is None:
            # Deployment does not exist

            logger.info(
                f"============== Deployment {image_url} does not exist =========="
            )
            logger.info(f"============== Create {image_url} deployment ==========")
            create_k8s_deployment_from_yaml(
                service_name=service_name,
                image_url_tag=image_url,
                imagePullPolicy=imagePullPolicy,
                desired_replicas=desired_replicas,
                file_name=k8s_file_name,
            )
        else:
            logger.info(
                f"=============== Deployment {service_name}:{curr_tag} exist ========== "
            )

            if (
                curr_status.unavailable_replicas is not None
                or curr_tag != image_tag
                or int(curr_status.replicas) != int(desired_replicas)
                or rollout is True
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

                if rollout is True:
                    logger.info(f"rollout is True")

                logger.info(f"========== Delete  {service_name}:{curr_tag}  ==========")
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
    is_local: bool = False,
    is_docker: bool = False,
    image_tag: str = None,
    ecr_repo: str = None,
    ecr_client=None,
    services_config_list: List[str] = None,
) -> List[str]:
    """
    Update worker and server's image_name and tag based on local or aws.

    """

    for service in services_config_list:
        # only inspect worker and server
        if service == "worker" or service == "server" or service =="celeryflower":
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
        # logger.info(result)
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
