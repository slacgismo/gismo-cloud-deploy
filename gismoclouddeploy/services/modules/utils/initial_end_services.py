from os import name
import time


from .WORKER_CONFIG import WORKER_CONFIG
from typing import List
from .check_aws import connect_aws_client, check_environment_is_aws
import logging
from .process_log import (
    process_logs_from_local,
    # analyze_local_logs_files,
)
from .eks_utils import scale_eks_nodes_and_wait
from .invoke_function import (
    invoke_docker_compose_down_and_remove,
    invoke_kubectl_delete_all_deployment,
    invoke_kubectl_delete_all_services,
    invoke_kubectl_delete_all_daemonset,
    invoke_kubectl_delete_all_po,
    invoke_kubectl_delete_namespaces,
    invoke_kubectl_delete_all_from_namspace,
    invoke_force_delete_namespace,
    invoke_docker_system_prune_all

)
from .command_utils import delete_files_from_bucket

from .sqs import delete_queue

from os.path import exists

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)




def delete_k8s_all_po_sev_deploy_daemonset(namespace: str="default"):
    # for server_info in server_list:
        # server_name = server_info['name']
        # namespace = server_info['namespace']
    logger.info("----------->.  Delete k8s deployment ----------->")
    delete_deploy = invoke_kubectl_delete_all_deployment(namespace=namespace)
    logger.info(delete_deploy)
    logger.info("----------->.  Delete k8s services ----------->")
    delete_svc = invoke_kubectl_delete_all_services(namespace=namespace)
    logger.info(delete_svc)
    # logger.info("----------->.  Delete k8s namespace ----------->")
    # delete_namespace = invoke_kubectl_delete_namespaces(namespace=namespace)
    # logger.info(delete_namespace)
    # logger.info("----------->.  Delete all daemonset ----------->")
    # delete_daemonset = invoke_kubectl_delete_all_daemonset()
    # logger.info(delete_daemonset)
    # logger.info("----------->.  Delete all po ----------->")
    # delete_po = invoke_kubectl_delete_all_po()
    # logger.info(delete_po)
    return 


def process_local_logs_and_upload_s3(
    # worker_config: WORKER_CONFIG = None,
    logs_file_path_name_local: str = None,
    saved_image_name_local: str = None,
    # saved_files_dict_local:dict= None,
    # saved_files_dict_cloud :dict = None,
    databucket: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
):
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )


    process_logs_from_local(
        logs_file_path_name_local=logs_file_path_name_local,
        saved_image_name_local=saved_image_name_local,
        s3_client=s3_client,
    )

    # logger.info("Update results to S3")
    # upload_results_to_s3(
    #     saved_files_dict_cloud=saved_files_dict_cloud,
    #     saved_files_dict_local=saved_files_dict_local,
    #     saved_bucket=databucket,
    #     aws_access_key=aws_access_key,
    #     aws_secret_access_key=aws_secret_access_key,
    #     aws_region=aws_region,
    # )


def initial_end_services(
    server_list : list = None,
    solver:dict = None,
    user_id:str = None,
    services_config_list: List[str] = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    scale_eks_nodes_wait_time: int = None,
    cluster_name: str = None,
    nodegroup_name: str = None,
    sqs_url: str = None,
    env:str = None,
    initial_process_time: float = None,
):

    # logger.info("=========== delete solver lic in bucket ============ ")
    # if solver['solver_name'] != "None":
    #     delete_solver_lic_from_bucket(
    #         saved_solver_bucket=solver['saved_solver_bucket'],
    #         solver_lic_file_name=solver['solver_lic_file_name'],
    #         saved_temp_path_in_bucket=solver['saved_temp_path_in_bucket'] + "/" + user_id,
    #         aws_access_key=aws_access_key,
    #         aws_secret_access_key=aws_secret_access_key,
    #         aws_region=aws_region,
    #     )
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    try:
        # check if totoal process time is longer than 60 sec
        current_time = time.time()
        process_time = float(current_time) - initial_process_time
        if process_time < 60:
            wait_time = process_time
            delay = 1
            while wait_time > 0 :
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
        logger.info(f"Delete {sqs_url} success")
        
    except Exception as e:
        logger.error(f"Delete queue failed {e}")

    
    for server_info in server_list:
        namespace = server_info['namespace']
        # delete_k8s_all_po_sev_deploy_daemonset(namespace= namespace)
        _delete_resource = invoke_kubectl_delete_all_from_namspace(namespace = namespace)
        print(_delete_resource)
        _delete_namespace = invoke_kubectl_delete_namespaces(namespace=namespace)
        # _delete_namespace= invoke_force_delete_namespace(namespace=namespace)
        print(f"Delete namespace :{namespace}")
        print(_delete_resource)
        print("==========================")
    if env == "AWS":
        logger.info("Scale down EKS nodes ")
        scale_eks_nodes_and_wait(
            scale_node_num=0,
            total_wait_time=scale_eks_nodes_wait_time,
            delay=3,
            cluster_name=cluster_name,
            nodegroup_name=nodegroup_name,
        )
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
    
    logger.info("Delete all docker images")
    # invoke_docker_system_prune_all()
        
        
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
        logger.error(f"Delete solver lic Failed{e}")
        logger.error(f"End services first. please fix this!!")
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


def upload_results_to_s3(
    saved_files_dict_local:dict = None,
    saved_files_dict_cloud:dict = None,
    saved_bucket: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:

    # saved_file_list = worker_config.filename
    logger.info("start update results")
    for key , localfile in saved_files_dict_local.items(): 
        file_local = saved_files_dict_local[key]
        file_aws =  saved_files_dict_cloud[key]
        logger.info(f"{key} file_local :{file_local} file_aws :{file_aws}")

        # check if local exist
        if exists(file_local):
            try:
                upload_file_to_s3(
                    bucket=saved_bucket,
                    source_file_local=file_local,
                    target_file_s3=file_aws,
                    aws_access_key=aws_access_key,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_region=aws_region,
                )
                logger.info(f"Save {file_local} to {file_aws}  on {saved_bucket} success")
            except Exception as e:
                logger.error(f"Save data on S3 failed {e}")
                raise Exception(e)
    return 




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
    logger.info(f"Upload {source_file_local} success")
