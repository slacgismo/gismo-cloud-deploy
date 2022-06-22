from os.path import exists
from re import A
import re
from typing import List, Dict
from unittest import result

import pandas as pd
import sys, json
import json
from botocore.exceptions import ClientError
import threading
from .process_log import read_all_csv_from_s3_and_parse_dates_from
from .sqs import purge_queue
from server.models.Configurations import AWS_CONFIG, WORKER_CONFIG
from .k8s_utils import (
    get_k8s_image_and_tag_from_deployment,
    create_k8s_deployment_from_yaml,
    get_k8s_pod_name,
)
from multiprocessing import Process

from .eks_utils import scale_eks_nodes_and_wait
from .invoke_function import (
    invoke_kubectl_delete_deployment,
    invoke_exec_docker_run_process_files,
    invoke_exec_k8s_run_process_files,
    invoke_docker_compose_down_and_remove,
    invoke_kubectl_delete_all_deployment,
    invoke_kubectl_delete_all_services,
    invoke_exec_k8s_ping_worker,
    invoke_exec_docker_check_task_status,
    invoke_exec_docker_ping_worker,
    invoke_exec_k8s_check_task_status,
)
from .process_log import process_logs_from_s3
from server.models.Configurations import (
    Configurations,
)
from server.utils import aws_utils
import time
from kubernetes import client, config
from modules.models.Node import Node
from .sqs import (
    receive_queue_message,
    delete_queue_message,
)
from io import StringIO
import os

from typing import Union
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def get_total_task_number(
    number: Union[int, None],
    aws_config: AWS_CONFIG = None,
    worker_config_json: str = None,
) -> int:
    total_task_num = 0

    if number is None:
        total_task_num = len(worker_config_json["default_process_files"]) + 1
        logger.info(" ========= Process default files in config.yam ========= ")
    else:
        if int(number) == 0:
            s3_client = aws_utils.connect_aws_client(
                client_name="s3",
                key_id=aws_config.aws_access_key,
                secret=aws_config.aws_secret_access_key,
                region=aws_config.aws_region,
            )

            all_files = aws_utils.list_files_in_bucket(
                bucket_name=worker_config_json["data_bucket"], s3_client=s3_client
            )
            number_files = len(all_files)
            total_task_num = len(all_files) + 1
            logger.info(
                f" ========= Process all {number_files} files in bucket ========= "
            )
        else:
            logger.info(f" ========= Process first {number} files in bucket ========= ")
            total_task_num = int(number) + 1
    return total_task_num


def invoke_process_files_based_on_number(
    number: Union[int, None],
    aws_config: AWS_CONFIG = None,
    worker_config_json: str = None,
    deployment_services_list: List[str] = None,
    is_docker: bool = False,
) -> None:

    worker_config_json["aws_access_key"] = aws_config.aws_access_key
    worker_config_json["aws_secret_access_key"] = aws_config.aws_secret_access_key
    worker_config_json["aws_region"] = aws_config.aws_region
    worker_config_json["sns_topic"] = aws_config.sns_topic
    worker_config_str = json.dumps(worker_config_json)
    counter = 25
    delay = 1
    while counter > 0:
        counter -= delay
        logger.info(f"Wait ...{counter} sec")
        time.sleep(delay)

    server_name = ""
    if is_docker:
        server_name = deployment_services_list["server"]["image_name"]
    else:
        server_name = get_k8s_pod_name(pod_name="server")

    if (
        check_and_wait_server_ready(
            is_docer=is_docker, server_name=server_name, wait_time=60, delay=1
        )
        is not True
    ):
        logger.error("Wait server ready failed")
        raise Exception(f"Wait {server_name} failed")

    if is_docker:
        docker_resp = invoke_exec_docker_run_process_files(
            config_params_str=worker_config_str,
            image_name=server_name,
            first_n_files=number,
        )
        logger.info(docker_resp)
    else:
        k8s_resp = invoke_exec_k8s_run_process_files(
            config_params_str=worker_config_str,
            pod_name=server_name,
            first_n_files=number,
        )
        logger.info(k8s_resp)
    logger.info("=============== >Invoke processifles command done")
    return


def process_logs_and_plot(
    worker_config: WORKER_CONFIG,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> None:

    s3_client = aws_utils.connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )

    logs_full_path_name = (
        worker_config.saved_logs_target_path
        + "/"
        + worker_config.saved_logs_target_filename
    )

    process_logs_from_s3(
        bucket=worker_config.saved_bucket,
        logs_file_path_name=logs_full_path_name,
        saved_image_name_aws=worker_config.saved_rumtime_image_name_aws,
        saved_image_name_local=worker_config.saved_rumtime_image_name_local,
        s3_client=s3_client,
    )
    logger.info(f"Success process logs from {worker_config.saved_logs_target_filename}")


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
            queue_url=dlq_url, MaxNumberOfMessages=1, sqs_client=sqs_client, wait_time=1
        )
        if "Messages" in messages:
            for msg in messages["Messages"]:
                msg_body = msg["Body"]
                receipt_handle = msg["ReceiptHandle"]
                logger.info(f"The message body: {msg_body}")

                # logger.info('Deleting message from the queue...')
                if delete_messages:
                    delete_queue_message(dlq_url, receipt_handle, sqs_client)

                logger.info(f"Received and deleted message(s) from {dlq_url}.")
                print(receipt_handle)
        else:
            logger.info("Clean DLQ message completed")
            return

        wait_time -= 1
        time.sleep(delay)


def check_nodes_status():
    """
    Check EKS node status
    """
    config.load_kube_config()
    v1 = client.CoreV1Api()
    response = v1.list_node()
    nodes = []
    # check confition
    for node in response.items:
        cluster = node.metadata.labels["alpha.eksctl.io/cluster-name"]
        nodegroup = node.metadata.labels["alpha.eksctl.io/nodegroup-name"]
        hostname = node.metadata.labels["kubernetes.io/hostname"]
        instance_type = node.metadata.labels["beta.kubernetes.io/instance-type"]
        region = node.metadata.labels["topology.kubernetes.io/region"]
        status = node.status.conditions[-1].status  # only looks the last
        status_type = node.status.conditions[-1].type  # only looks the last
        node_obj = Node(
            cluster=cluster,
            nodegroup=nodegroup,
            hostname=hostname,
            instance_type=instance_type,
            region=region,
            status=status,
            status_type=status_type,
        )

        nodes.append(node_obj)
        if bool(status) is not True:
            logger.info(f"{hostname} is not ready status:{status}")
            return False
    for node in nodes:
        logger.info(f"{node.hostname} is ready")
    return True


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
        if service == "worker" or service == "server":
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


def combine_files_to_file(
    bucket_name: str,
    source_folder: str,
    target_folder: str,
    target_filename: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> None:
    """
    Combine all files in sorce folder and save into target folder and target file.
    After the process is completed, all files in source folder will be deleted.
    """
    print("combine files ---->")
    s3_client = aws_utils.connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    filter_files = list_files_in_folder_of_bucket(bucket_name, source_folder, s3_client)

    if not filter_files:
        logger.warning("No tmp file in folder")
        return
        # raise Exception("Error: No saved tmp file found ")
    contents = []
    for file in filter_files:
        df = aws_utils.read_csv_from_s3(bucket_name, file, s3_client)
        contents.append(df)
    frame = pd.concat(contents, axis=0, ignore_index=True)
    csv_buffer = StringIO()
    frame.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    try:
        aws_utils.to_s3(
            bucket=bucket_name,
            file_path=target_folder,
            filename=target_filename,
            content=content,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        print(f"Save to {target_filename} success!!")
        # delete files
        for file in filter_files:
            delete_files_from_bucket(bucket_name, file, s3_client)
    except Exception as e:
        print(f"save to s3 error or delete files error ---> {e}")
        raise e


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


def initial_end_services(
    worker_config: WORKER_CONFIG = None,
    aws_config: AWS_CONFIG = None,
    is_local: bool = False,
    is_docker: bool = False,
    delete_nodes_after_processing: bool = False,
    is_build_image: bool = False,
    services_config_list: List[str] = None,
):
    try:
        save_data_file = (
            worker_config.saved_data_target_path_local
            + "/"
            + worker_config.saved_target_filename
        )
        save_logs_file = (
            worker_config.saved_logs_target_path
            + "/"
            + worker_config.saved_logs_target_filename
        )
        aws_utils.save_user_logs_data_from_dynamodb(
            table_name=worker_config.dynamodb_tablename,
            user_id=worker_config.user_id,
            saved_bucket=worker_config.saved_bucket,
            save_data_file=save_data_file,
            save_logs_file=save_logs_file,
            aws_access_key=aws_config.aws_access_key,
            aws_secret_key=aws_config.aws_secret_access_key,
            aws_region=aws_config.aws_region,
        )
    except Exception as e:
        logger.error(f"Failed to save data and logs from dynamodb {e}")
        raise e
    try:
        # download logs data
        source_log_file_s3 = (
            worker_config.saved_logs_target_path
            + "/"
            + worker_config.saved_logs_target_filename
        )
        target_log_file_local = (
            worker_config.saved_data_target_path_local
            + "/"
            + worker_config.saved_logs_target_filename
        )
        download_file_from_s3(
            bucket_name=worker_config.saved_bucket,
            source_file=source_log_file_s3,
            target_file=target_log_file_local,
            aws_access_key=aws_config.aws_access_key,
            aws_secret_access_key=aws_config.aws_secret_access_key,
            aws_region=aws_config.aws_region,
        )
    except Exception as e:
        logger.error(f"Failed to download logs from s3 {e}")
        raise e
    try:
        # download results data
        data_source_file_s3 = (
            worker_config.saved_data_target_path
            + "/"
            + worker_config.saved_target_filename
        )
        data_target_file_local = (
            worker_config.saved_data_target_path_local
            + "/"
            + worker_config.saved_target_filename
        )
        download_file_from_s3(
            bucket_name=worker_config.saved_bucket,
            source_file=data_source_file_s3,
            target_file=data_target_file_local,
            aws_access_key=aws_config.aws_access_key,
            aws_secret_access_key=aws_config.aws_secret_access_key,
            aws_region=aws_config.aws_region,
        )
    except Exception as e:
        logger.error(f"Failed to download data file from s3 {e}")
        raise e
    # try:
    #     combine_files_to_file(
    #         bucket_name=worker_config.saved_bucket,
    #         source_folder=worker_config.saved_tmp_path,
    #         target_folder=worker_config.saved_data_target_path,
    #         target_filename=worker_config.saved_target_filename,
    #         aws_access_key=aws_config.aws_access_key,
    #         aws_secret_access_key=aws_config.aws_secret_access_key,
    #         aws_region=aws_config.aws_region,
    #     )
    # except Exception:
    #     raise Exception("Combine file failed")
    # try:
    #     source_file = (
    #         worker_config.saved_data_target_path + "/" + worker_config.saved_target_filename
    #     )
    #     target_file = (
    #         worker_config.saved_data_target_path_local
    #         + "/"
    #         + worker_config.saved_target_filename
    #     )
    # # download results data
    # download_file_from_s3(
    #     bucket_name=worker_config.saved_bucket,
    #     source_file=source_file,
    #     target_file=target_file,
    #     aws_access_key=aws_config.aws_access_key,
    #     aws_secret_access_key=aws_config.aws_secret_access_key,
    #     aws_region=aws_config.aws_region,
    # )
    # except Exception:
    #     raise Exception("Download saved file failed")
    # save logs from dynamodb to s3
    # try:
    #     logger.info("========= query logs from user")
    #     # aws_utils.query_user_items_from_dynamodb(
    #     #     table_name=worker_config.dynamodb_tablename,
    #     #     user=worker_config.user_id,
    #     #     aws_access_key=aws_config.aws_access_key,
    #     #     aws_secret_key= aws_config.aws_secret_access_key,
    #     #     aws_region=aws_config.aws_region
    #     # )
    #     # aws_utils.save_logs_from_dynamodb_to_s3(
    #     #     table_name=worker_config.dynamodb_tablename,
    #     #     saved_bucket=worker_config.saved_bucket,
    #     #     saved_file_path=worker_config.saved_logs_target_path,
    #     #     saved_filename=worker_config.saved_logs_target_filename,
    #     #     aws_access_key=aws_config.aws_access_key,
    #     #     aws_secret_access_key=aws_config.aws_secret_access_key,
    #     #     aws_region=aws_config.aws_region,
    #     # )
    # # download logs data
    # source_log_file = (
    #     worker_config.saved_logs_target_path
    #     + "/"
    #     + worker_config.saved_logs_target_filename
    # )
    # target_log_file = (
    #     worker_config.saved_data_target_path_local
    #     + "/"
    #     + worker_config.saved_logs_target_filename
    # )
    # download_file_from_s3(
    #     bucket_name=worker_config.saved_bucket,
    #     source_file=source_log_file,
    #     target_file=target_log_file,
    #     aws_access_key=aws_config.aws_access_key,
    #     aws_secret_access_key=aws_config.aws_secret_access_key,
    #     aws_region=aws_config.aws_region,
    # )
    # except Exception:
    #     raise Exception("Save logs files failed")
    # remove dynamodb
    # try:
    #     aws_utils.remove_all_items_from_dynamodb(
    #         user = worker_config.user_id,
    #         table_name=worker_config.dynamodb_tablename,
    #         aws_access_key=aws_config.aws_access_key,
    #         aws_secret_access_key=aws_config.aws_secret_access_key,
    #         aws_region=aws_config.aws_region,
    #     )
    # except Exception:
    #     raise Exception("Remove items from dynamodb failed")

    # get save data from log file

    # remove solver lic
    logger.info("=========== delete solver lic in bucket ============ ")
    delete_solver_lic_from_bucket(
        saved_solver_bucket=worker_config.solver.saved_solver_bucket,
        solver_lic_file_name=worker_config.solver.solver_lic_file_name,
        saved_temp_path_in_bucket=worker_config.solver.saved_temp_path_in_bucket,
        aws_access_key=aws_config.aws_access_key,
        aws_secret_access_key=aws_config.aws_secret_access_key,
        aws_region=aws_config.aws_region,
    )
    logs_full_path_name = (
        worker_config.saved_logs_target_path
        + "/"
        + worker_config.saved_logs_target_filename
    )
    s3_client = aws_utils.connect_aws_client(
        client_name="s3",
        key_id=aws_config.aws_access_key,
        secret=aws_config.aws_secret_access_key,
        region=aws_config.aws_region,
    )
    process_logs_from_s3(
        bucket=worker_config.saved_bucket,
        logs_file_path_name=logs_full_path_name,
        saved_image_name_local=worker_config.saved_rumtime_image_name_local,
        saved_image_name_aws=worker_config.saved_rumtime_image_name_aws,
        s3_client=s3_client,
    )

    if aws_utils.check_environment_is_aws() and delete_nodes_after_processing is True:
        logger.info("Delete node after processing")
        scale_eks_nodes_and_wait(
            scale_node_num=aws_config.eks_nodes_number,
            total_wait_time=aws_config.scale_eks_nodes_wait_time,
            delay=2,
            cluster_name=aws_config.cluster_name,
            nodegroup_name=aws_config.nodegroup_name,
        )

        # Remove services.

        remove_running_services(
            is_build_image=is_build_image,
            is_docker=is_docker,
            is_local=is_local,
            aws_config=aws_config,
            services_config_list=services_config_list,
        )
    try:
        sqs_client = aws_utils.connect_aws_client(
            client_name="sqs",
            key_id=aws_config.aws_access_key,
            secret=aws_config.aws_secret_access_key,
            region=aws_config.aws_region,
        )
        purge_queue(queue_url=aws_config.sqs_url, sqs_client=sqs_client)
    except Exception as e:
        logger.error(f"Cannot purge queue.{e}")
        return
    return


def remove_running_services(
    is_build_image: bool = False,
    is_docker: bool = False,
    is_local: bool = False,
    aws_config: AWS_CONFIG = None,
    services_config_list: List[str] = None,
) -> None:
    if is_build_image:
        if is_docker:
            # delete local docker images
            logger.info("Delete local docker image")
            invoke_docker_compose_down_and_remove()
        else:
            if is_local:
                logger.info("Remove local k8s svc and deployment")
                invoke_kubectl_delete_all_deployment()
                invoke_kubectl_delete_all_services()
            else:
                logger.info("----------->.  Delete Temp ECR image ----------->")
                ecr_client = aws_utils.connect_aws_client(
                    client_name="ecr",
                    key_id=aws_config.aws_access_key,
                    secret=aws_config.aws_secret_access_key,
                    region=aws_config.aws_region,
                )
                for service in services_config_list:
                    if service == "worker" or service == "server":
                        image_tag = services_config_list[service]["image_tag"]
                        aws_utils.delete_ecr_image(
                            ecr_client=ecr_client,
                            image_name=service,
                            image_tag=image_tag,
                        )
    return


def check_solver_and_upload(
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


def delete_solver_lic_from_bucket(
    saved_solver_bucket: str = None,
    saved_temp_path_in_bucket: str = None,
    solver_lic_file_name: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:
    if (
        saved_solver_bucket is None
        or saved_temp_path_in_bucket is None
        or solver_lic_file_name is None
        or aws_access_key is None
        or aws_secret_access_key is None
        or aws_region is None
    ):
        logger.warning("No input parameters")
        return
    try:
        s3_client = aws_utils.connect_aws_client(
            "s3", key_id=aws_access_key, secret=aws_secret_access_key, region=aws_region
        )
        full_path = saved_temp_path_in_bucket + "/" + solver_lic_file_name
        delete_files_from_bucket(
            bucket_name=saved_solver_bucket, full_path=full_path, s3_client=s3_client
        )
    except Exception as e:
        logger.error(f"Delete solver lic errorf{e}")
        raise e
    return


def check_and_wait_server_ready(
    is_docer: bool = False, server_name: str = None, wait_time: int = 30, delay: int = 1
) -> bool:
    while wait_time > 0:
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

        wait_time -= delay
        time.sleep(delay)
        if wait_time <= 0:
            logger.error(f"Ping {server_name} over time")
            return

    while wait_time > 0:

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
        # conver json to
        res_json = {}
        dataform = str(result).strip("'<>() ").replace("'", '"').strip("\n")

        try:
            res_json = json.loads(dataform)
            status = res_json["task_status"]
            logger.info(f" ==== Check {server_name} Status: {status}====")
            if status == "SUCCESS":
                return True
        except Exception as e:
            logger.info(f"load json failed res:{result} {e}")
            return False

        wait_time -= delay
        time.sleep(delay)
    logger.error("check server reday orvertime")
    return False


def get_saved_data_from_logs(
    logs_file_path_name: str = None,
    s3_client=None,
    saved_file_name: str = None,
    bucket: str = None,
) -> None:
    df = read_all_csv_from_s3_and_parse_dates_from(
        bucket_name=bucket,
        file_path_name=logs_file_path_name,
        dates_column_name="timestamp",
        s3_client=s3_client,
    )

    print(df.head())
