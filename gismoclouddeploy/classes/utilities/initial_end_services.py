import time
from typing import List

from ..constants.DevEnvironments import DevEnvironments
from .check_aws import connect_aws_client
import logging
from .eks_utils import scale_eks_nodes_and_wait
from .invoke_function import (
    invoke_kubectl_delete_namespaces,
    invoke_kubectl_delete_all_from_namspace,
)

from .sqs import delete_queue
import logging


def initial_end_services(
    server_list: list = None,
    services_config_list: List[str] = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    scale_eks_nodes_wait_time: int = None,
    cluster_name: str = None,
    nodegroup_name: str = None,
    sqs_url: str = None,
    env: str = None,
    initial_process_time: float = None,
):

    try:
        # check if totoal process time is longer than 60 sec
        current_time = time.time()
        process_time = float(current_time) - initial_process_time
        if process_time < 60:
            wait_time = process_time
            delay = 1
            while wait_time > 0:
                logging.info(f"Wait {wait_time}")
                wait_time -= delay
                time.sleep(delay)

        sqs_client = connect_aws_client(
            client_name="sqs",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
        res = delete_queue(queue_url=sqs_url, sqs_client=sqs_client)
        logging.info(f"Delete {sqs_url} success")

    except Exception as e:
        logging.error(f"Delete queue failed {e}")

    for server_info in server_list:
        namespace = server_info["namespace"]

        logging.info(f"Clean all resources in: {namespace}")
        invoke_kubectl_delete_all_from_namspace(namespace=namespace)
        invoke_kubectl_delete_namespaces(namespace=namespace)
        logging.info(f"Delete namespace:{namespace}")

    if env == DevEnvironments.AWS.name:
        logging.info("Scale down EKS nodes ")
        scale_eks_nodes_and_wait(
            scale_node_num=0,
            total_wait_time=scale_eks_nodes_wait_time,
            delay=15,
            cluster_name=cluster_name,
            nodegroup_name=nodegroup_name,
        )
        logging.info("-----------  Delete Temp ECR image -----------")
        ecr_client = connect_aws_client(
            client_name="ecr",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
        for service in services_config_list:
            if service == "worker" or service == "server":
                image_tag = services_config_list[service]["image_tag"]
                delete_ecr_image(
                    ecr_client=ecr_client,
                    image_name=service,
                    image_tag=image_tag,
                )

    # logging.info("Delete all docker images")
    # invoke_docker_system_prune_all()

    return


def delete_ecr_image(
    ecr_client=None, image_name: str = None, image_tag: str = None
) -> str:

    if ecr_client is None or image_name is None or image_tag is None:
        raise Exception("Input parameters error")
    if image_tag == "latest" or image_tag == "develop":
        raise Exception(f"Can not remove {image_tag}")

    # check if image tag exist
    try:
        check_ecr_tag_exists(
            image_tag=image_tag, image_name=image_name, ecr_client=ecr_client
        )
    except Exception as e:
        raise Exception(f"{image_name}:{image_tag} does not exist")

    response = ecr_client.list_images(
        repositoryName=image_name, filter={"tagStatus": "TAGGED"}
    )
    delete_image_ids = [
        image for image in response["imageIds"] if image["imageTag"] == image_tag
    ]

    delete_resp = ecr_client.batch_delete_image(
        repositoryName=image_name, imageIds=delete_image_ids
    )
    return delete_resp


def check_ecr_tag_exists(
    image_tag: str = None, image_name: str = None, ecr_client=None
) -> bool:
    """
    Check if ECR name/tag exist.

    Parameters
    ----------
    :param str image_tag: Image name
    :param str image_name: Image tag
    :param str ecr_client: boto3 ecr client object

    Returns
    -------
    :return bool: Return True if ECR name/tag exist else return False
    """
    response = ecr_client.describe_images(
        repositoryName=image_name, filter={"tagStatus": "TAGGED"}
    )
    try:
        response = ecr_client.describe_images(
            repositoryName=f"worker", filter={"tagStatus": "TAGGED"}
        )
        for i in response["imageDetails"]:
            if image_tag in i["imageTags"]:
                return True
        return False
    except Exception as e:
        return False


def upload_file_to_s3(
    bucket: str = None,
    source_file_local: str = None,
    target_file_s3: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:
    """
    Upload file to S3 bucket

    """

    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    response = s3_client.upload_file(source_file_local, bucket, target_file_s3)
    logging.info(f"Upload {source_file_local} success")
