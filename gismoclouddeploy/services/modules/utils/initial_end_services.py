from .WORKER_CONFIG import WORKER_CONFIG
from typing import List
from .check_aws import connect_aws_client, check_environment_is_aws
import logging
from .process_log import process_logs_from_s3
from .eks_utils import scale_eks_nodes_and_wait
from .invoke_function import invoke_docker_compose_down_and_remove
from .command_utils import delete_files_from_bucket
from .sqs import purge_queue

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def initial_end_services(
    worker_config: WORKER_CONFIG = None,
    is_local: bool = False,
    is_docker: bool = False,
    delete_nodes_after_processing: bool = False,
    is_build_image: bool = False,
    services_config_list: List[str] = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    sqs_url: str = None,
    scale_eks_nodes_wait_time: int = None,
    cluster_name: str = None,
    nodegroup_name: str = None,
):

    logger.info("=========== delete solver lic in bucket ============ ")
    delete_solver_lic_from_bucket(
        saved_solver_bucket=worker_config.solver.saved_solver_bucket,
        solver_lic_file_name=worker_config.solver.solver_lic_file_name,
        saved_temp_path_in_bucket=worker_config.user_id,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
    )
    logs_full_path_name = (
        worker_config.saved_path + "/" + worker_config.saved_logs_target_filename
    )
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )

    plot_full_path_name = (
        worker_config.saved_path + "/" + worker_config.saved_rumtime_image_name
    )
    process_logs_from_s3(
        bucket=worker_config.saved_bucket,
        logs_file_path_name=logs_full_path_name,
        saved_image_name_local=plot_full_path_name,
        saved_image_name_aws=plot_full_path_name,
        s3_client=s3_client,
    )

    if check_environment_is_aws() and delete_nodes_after_processing is True:
        logger.info("======= >Delete node after processing")
        scale_eks_nodes_and_wait(
            scale_node_num=0,
            total_wait_time=scale_eks_nodes_wait_time,
            delay=3,
            cluster_name=cluster_name,
            nodegroup_name=nodegroup_name,
        )

    # Remove services.
    if check_environment_is_aws() and is_build_image:
        logger.info("----------->.  Delete Temp ECR image ----------->")
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
    remove_running_services(
        is_docker=is_docker,
        services_config_list=services_config_list,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
    )

    try:
        sqs_client = connect_aws_client(
            client_name="sqs",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
        purge_queue(queue_url=sqs_url, sqs_client=sqs_client)
    except Exception as e:
        logger.error(f"Cannot purge queue.{e}")
        return
    return


def remove_running_services(
    is_build_image: bool = False,
    is_docker: bool = False,
    services_config_list: List[str] = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:
    if is_build_image:
        if is_docker:
            # delete local docker images
            logger.info("Delete local docker image")
            invoke_docker_compose_down_and_remove()
        else:

            logger.info("----------->.  Delete Temp ECR image ----------->")
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
        s3_client = connect_aws_client(
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

    # delete ecr tag
    response = ecr_client.list_images(
        repositoryName=image_name, filter={"tagStatus": "TAGGED"}
    )
    delete_image_ids = [
        image for image in response["imageIds"] if image["imageTag"] == image_tag
    ]
    # print(delete_image_ids)
    delete_resp = ecr_client.batch_delete_image(
        repositoryName=image_name, imageIds=delete_image_ids
    )
    return delete_resp


def check_ecr_tag_exists(
    image_tag: str = None, image_name: str = None, ecr_client=None
) -> bool:
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
