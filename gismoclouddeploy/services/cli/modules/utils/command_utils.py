from server import models
from .eks_utils import scale_nodes_and_wait, create_or_update_k8s
from .read_wirte_io import import_yaml_and_convert_to_json_str
from .invoke_function import invoke_exec_run_process_files
from .process_log import process_logs_from_s3

from server.utils import aws_utils

import time
from kubernetes import client, config
from modules.models.Node import Node
from .sqs import (
    receive_queue_message,
    delete_queue_message,
)

from typing import Union
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def check_environment_setup(
    config_params_obj: models.Configurations, rollout: bool
) -> None:

    # check node status from local or AWS
    if config_params_obj.environment == "AWS":
        logger.info(" ============ Running on AWS ===============")
        config_params_obj.container_type = "kubernetes"
        config_params_obj.container_name = "webapp"

        scale_nodes_and_wait(
            scale_node_num=int(config_params_obj.eks_nodes_number),
            counter=int(config_params_obj.scale_eks_nodes_wait_time),
            delay=1,
            config_params_obj=config_params_obj,
        )
        # create or update k8s setting based on yaml files
        try:
            # create_or_update_k8s(config_params_obj=config_params_obj,rollout=rollout, env="aws")
            create_or_update_k8s(
                config_params_obj=config_params_obj,
                rollout=rollout,
                env="AWS",
            )
        except Exception as e:
            logger.error(f"Create or update k8s error :{e}")
            raise e

    else:
        # local env
        if config_params_obj.container_type == "kubernetes":
            # check if k8s and webapp exist
            try:
                # create_or_update_k8s(config_params_obj=config_params_obj,rollout=rollout, env="local")
                create_or_update_k8s(
                    config_params_obj=config_params_obj,
                    rollout=rollout,
                    env="local",
                )
            except Exception as e:
                logger.error(f"Create or update k8s error :{e}")
                raise e

    return


def invoke_process_files_based_on_number(
    number: Union[int, None], config_params_obj: models.Configurations, config_yaml: str
) -> int:
    total_task_num = 0
    try:
        config_params_str = import_yaml_and_convert_to_json_str(
            yaml_file=config_yaml,
            aws_access_key=config_params_obj.aws_access_key,
            aws_secret_access_key=config_params_obj.aws_secret_access_key,
            aws_region=config_params_obj.aws_region,
            sns_topic=config_params_obj.sns_topic,
        )
    except Exception as e:
        logger.error(f"Convert Configrations to json failed:{e}")
        raise e

    if number is None:
        logger.info(" ========= Process default files in config.yam ========= ")
        try:

            invoke_exec_run_process_files(
                config_params_str=config_params_str,
                container_type=config_params_obj.container_type,
                container_name=config_params_obj.container_name,
                first_n_files=number,
            )

            total_task_num = len(config_params_obj.files) + 1
        except Exception as e:
            logger.error(f"Process default files failed :{e}")
            raise e
    else:
        try:
            total_task_num = 0
            if int(number) == 0:

                s3_client = aws_utils.connect_aws_client(
                    client_name="s3",
                    key_id=config_params_obj.aws_access_key,
                    secret=config_params_obj.aws_secret_access_key,
                    region=config_params_obj.aws_region,
                )

                all_files = aws_utils.list_files_in_bucket(
                    bucket_name=config_params_obj.bucket, s3_client=s3_client
                )
                number_files = len(all_files)
                total_task_num = len(all_files) + 1
                logger.info(
                    f" ========= Process all {number_files} files in bucket ========= "
                )
            else:
                logger.info(
                    f" ========= Process first {number} files in bucket ========= "
                )
                total_task_num = int(number) + 1
            try:
                invoke_exec_run_process_files(
                    config_params_str=config_params_str,
                    container_type=config_params_obj.container_type,
                    container_name=config_params_obj.container_name,
                    first_n_files=number,
                )

            except Exception as e:
                logger.error(f"Process first {number} files failed :{e}")
                raise e

        except Exception as e:
            raise Exception(f"Input Number Error :{e}")
    logger.info(f"total_task_num :{total_task_num}")
    return total_task_num


def process_logs_and_plot(config_params_obj: models.Configurations) -> None:

    s3_client = aws_utils.connect_aws_client(
        client_name="s3",
        key_id=config_params_obj.aws_access_key,
        secret=config_params_obj.aws_secret_access_key,
        region=config_params_obj.aws_region,
    )

    logs_full_path_name = (
        config_params_obj.saved_logs_target_path
        + "/"
        + config_params_obj.saved_logs_target_filename
    )
    process_logs_from_s3(
        config_params_obj.saved_bucket,
        logs_full_path_name,
        "results/runtime.png",
        s3_client,
    )
    logger.info(
        f"Success process logs from {config_params_obj.saved_logs_target_filename}"
    )


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
