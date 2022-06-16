from re import A
from typing import List, Dict
import json
from server.models.Configurations import AWS_CONFIG, WORKER_CONFIG
from .k8s_utils import (
    get_k8s_image_and_tag_from_deployment,
    create_k8s_deployment_from_yaml,
    get_k8s_pod_name,
)
from .invoke_function import (
    invoke_kubectl_delete_deployment,
    invoke_docker_check_image_exist,
    invoke_exec_docker_run_process_files,
    invoke_exec_k8s_run_process_files,
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


from typing import Union
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def invoke_process_files_based_on_number(
    number: Union[int, None],
    aws_config: AWS_CONFIG = None,
    worker_config_json: str = None,
    deployment_services_list: List[str] = None,
    is_docker: bool = False,
) -> int:

    total_task_num = 0

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
    logger.info(f"total_task_num :{total_task_num}")
    worker_config_json["aws_access_key"] = aws_config.aws_access_key
    worker_config_json["aws_secret_access_key"] = aws_config.aws_secret_access_key
    worker_config_json["aws_region"] = aws_config.aws_region
    worker_config_json["sns_topic"] = aws_config.sns_topic
    worker_config_str = json.dumps(worker_config_json)
    if is_docker:
        logger.info("------docker -----------")
        image_name = deployment_services_list["server"]["image_name"]
        # image_tag = deployment_services_list["server"]["image_tag"]
        # image_name_tag = f"{image_name}:{image_tag}"
        docker_resp = invoke_exec_docker_run_process_files(
            config_params_str=worker_config_str,
            image_name=image_name,
            first_n_files=number,
        )
        logger.info(docker_resp)
    else:
        logger.info("------ k8s -----------")
        server_pod_name = get_k8s_pod_name(pod_name="server")
        logger.info(f"server po name: {server_pod_name}")
        k8s_resp = invoke_exec_k8s_run_process_files(
            config_params_str=worker_config_str,
            pod_name=str(server_pod_name),
            first_n_files=number,
        )
        logger.info(k8s_resp)

    return total_task_num


# def invoke_process_files_based_on_number(
#     number: Union[int, None],
#     config_params_obj: Configurations = None,
#     config_yaml: str = None,
#     is_docker: bool = False,
# ) -> int:

#     total_task_num = 0
#     try:
#         config_params_str = import_yaml_and_convert_to_json_str(
#             yaml_file=config_yaml,
#             aws_access_key=config_params_obj.aws_access_key,
#             aws_secret_access_key=config_params_obj.aws_secret_access_key,
#             aws_region=config_params_obj.aws_region,
#             sns_topic=config_params_obj.sns_topic,
#         )
#     except Exception as e:
#         logger.error(f"Convert Configrations to json failed:{e}")
#         raise e
#     total_task_num = 0
#     if number is None:
#         total_task_num = len(config_params_obj.files) + 1
#         logger.info(" ========= Process default files in config.yam ========= ")
#     else:
#         if int(number) == 0:
#             s3_client = aws_utils.connect_aws_client(
#                 client_name="s3",
#                 key_id=config_params_obj.aws_access_key,
#                 secret=config_params_obj.aws_secret_access_key,
#                 region=config_params_obj.aws_region,
#             )

#             all_files = aws_utils.list_files_in_bucket(
#                 bucket_name=config_params_obj.bucket, s3_client=s3_client
#             )
#             number_files = len(all_files)
#             total_task_num = len(all_files) + 1
#             logger.info(
#                 f" ========= Process all {number_files} files in bucket ========= "
#             )
#         else:
#             logger.info(f" ========= Process first {number} files in bucket ========= ")
#             total_task_num = int(number) + 1
#     logger.info(f"total_task_num :{total_task_num}")

#     if is_docker:
#         logger.info("------docker -----------")
#         image_name = config_params_obj.deployment_services_list["server"]["image_name"]
#         image_tag = config_params_obj.deployment_services_list["server"]["image_tag"]
#         image_name_tag = f"{image_name}:{image_tag}"
#         docker_resp = invoke_exec_docker_run_process_files(
#             config_params_str=config_params_str,
#             image_name=image_name,
#             first_n_files=number,
#         )
#         logger.info(docker_resp)
#     else:
#         logger.info("------ k8s -----------")
#         server_pod_name = get_k8s_pod_name(pod_name="server")
#         logger.info(f"server po name: {server_pod_name}")
#         k8s_resp = invoke_exec_k8s_run_process_files(
#             config_params_str=config_params_str,
#             pod_name=str(server_pod_name),
#             first_n_files=number,
#         )
#         logger.info(k8s_resp)

#     return total_task_num


def process_logs_and_plot(config_params_obj: Configurations) -> None:

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
        bucket=config_params_obj.saved_bucket,
        logs_file_path_name=logs_full_path_name,
        saved_image_name_aws=config_params_obj.saved_rumtime_image_name_aws,
        saved_image_name_local=config_params_obj.saved_rumtime_image_name_local,
        s3_client=s3_client
        # config_params_obj.saved_bucket,
        # logs_full_path_name,
        # "results/runtime.png",
        # s3_client,
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
                print("====================")
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
                logger.info("update services config in local")
                # update image policy
                services_config_list[service]["imagePullPolicy"] = imagePullPolicy
            else:
                logger.info("update services image on AWS")
                image_base_url = f"{ecr_repo}/{service}"
                services_config_list[service]["image_name"] = image_base_url

            # Updated image tag
            services_config_list[service]["image_tag"] = image_tag

    return services_config_list

    # if is_local is False:


# def update_config_obj_image_name_and_tag_according_to_env(
#     is_local: bool = False,
#     image_tag: str = None,
#     ecr_repo: str = None,
#     ecr_client=None,
#     config_params_obj: Configurations = None,
# ) -> Configurations:

#     services_list = ["worker", "server"]

#     if is_local is False:
#         logger.info("Running on AWS")
#         # wait eks node status
#         for service in services_list:
#             image_base_url = f"{ecr_repo}/{service}"
#             # check if ecr exist
#             if (
#                 aws_utils.check_ecr_tag_exists(
#                     ecr_client=ecr_client,
#                     ecr_repo=ecr_repo,
#                     image_name=service,
#                     image_tag=image_tag
#                 )
#                 is False
#             ):
#                 logger.error(f"{image_base_url} does not exist")
#                 return

#             # update image name
#             # for a in vars(config_params_obj.k8s_config.deployment_services_list):
#             #     if a == "worker":
#             #         config_params_obj.k8s_config.deployment_services_list.
#             # print(vars(config_params_obj.k8s_config.deployment_services_list))
#             # for index, service_info in config_params_obj.k8s_config.deployment_services_list.items():
#             #     if service in service_info:
#             #         # tt = config_params_obj.k8s_config.deployment_services_list[index]
#             #         logger.info(index)
#             # config_params_obj.deployment_services_list[service][
#             #     "image_name"
#             # ] = image_base_url
#             # config_params_obj.deployment_services_list[service]["image_tag"] = image_tag
#     else:
#         logger.info("Running in Local")
#         for service in services_list:
#             image_url = f"{service}:{image_tag}"
#             imagePullPolicy = "IfNotPresent"
#             # check if image exist
#             try:
#                 invoke_docker_check_image_exist(image_name=image_url)
#             except Exception as e:
#                 logger.info(f"docker {image_url} does not exist")
#                 return
#             # updat image tag
#             # config_params_obj.deployment_services_list[service]["image_tag"] = image_tag
#             # config_params_obj.deployment_services_list[service][
#             #     "imagePullPolicy"
#             # ] = imagePullPolicy

#             # service_info = filter(lambda key: service in key,config_params_obj.k8s_config.deployment_services_list )
#             # print(list(service_info))

#     return config_params_obj
