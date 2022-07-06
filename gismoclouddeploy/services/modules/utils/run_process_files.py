import time


from .command_utils import (
    check_solver_and_upload,
    update_config_json_image_name_and_tag_base_on_env,
    create_or_update_k8s_deployment,
    checck_server_ready_and_get_name,
    send_command_to_server,
)
from .initial_end_services import initial_end_services


from .long_pulling_sqs import long_pulling_sqs
from .AWS_CONFIG import AWS_CONFIG
from .WORKER_CONFIG import WORKER_CONFIG
from .check_aws import connect_aws_client, check_environment_is_aws

from .modiy_config_parameters import modiy_config_parameters
import logging
import socket
import threading
from .invoke_function import (
    invoke_docker_compose_build_and_run,
    invoke_docker_compose_build,
    invoke_tag_image,
    invoke_ecr_validation,
    invoke_push_image,
    invoke_eks_updagte_kubeconfig,
)
from .k8s_utils import check_k8s_services_exists, create_k8s_svc_from_yaml

from .eks_utils import scale_eks_nodes_and_wait, wait_pod_ready

from .sqs import clean_user_previous_sqs_message
from multiprocessing.dummy import Process
from .process_log import analyze_local_logs_files

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def run_process_files(
    number: int = 1,
    delete_nodes: bool = False,
    configfile: str = None,
    rollout: bool = False,
    image_tag: str = None,
    is_docker: bool = False,
    is_local: bool = False,
    is_build_image: bool = False,
    nodesscale: int = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    sqs_url: str = None,
    sns_topic: str = None,
    dlq_url: str = None,
    ecr_repo: str = None,
) -> None:
    """
    Proccess files in defined bucket
    :param number:      number of first n files in bucket. Default value is `None`.
                        If number is None, this application process defined files in config.yaml.
                        If number is 0, this application processs all files in the defined bucket in config.yaml.
                        If number is an integer, this applicaion process the first `number` files in the defined bucket in config.yaml.
    :param delete_nodes: Enable deleting eks node after complete this application. Default value is False.
    :param configfile:  Define config file name. Default value is "./config/config.yaml"
    :param rollout:     Enable delete current k8s deployment and re-deployment. Default value is False
    :param image_tag:   Specifiy the image tag. Default value is 'latest'
    :param is_docker:   Default value is False. If it is True, the services run in docker environment.
                        Otherwise, the services run in k8s environment.
    :param is_build_image:    Build a temp image and use it. If on AWS k8s environment, \
                        build and push image to ECR with temp image tag. These images will be deleted after used.\
                        If you would like to preserve images, please use build-image command instead
    """
    # check aws credential
    start_time = time.time()

    config_json = modiy_config_parameters(
        configfile=configfile,
        nodesscale=nodesscale,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
        sqs_url=sqs_url,
        sns_topic=sns_topic,
        dlq_url=dlq_url,
        ecr_repo=ecr_repo,
    )

    user_id = config_json["worker_config"]["user_id"]
    worker_config_obj = WORKER_CONFIG(config_json["worker_config"])
    aws_config_obj = AWS_CONFIG(config_json["aws_config"])
    services_config_list = config_json["services_config_list"]
    ecr_client = connect_aws_client(
        client_name="ecr",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    # check environments , check image name and tag exist. Update images name and tag to object
    is_local = True

    if check_environment_is_aws():
        logger.info("======== Running on AWS ========")
        is_local = False

    services_config_list = update_config_json_image_name_and_tag_base_on_env(
        is_local=is_local,
        image_tag=image_tag,
        ecr_client=ecr_client,
        ecr_repo=ecr_repo,
        services_config_list=services_config_list,
    )

    # analyze_local_logs_files(
    #     instanceType="instanceType",
    #     logs_file_path_name="./results/logs-644-15.csv",
    #     initial_process_time=0,
    #     total_process_time=100,
    #     eks_nodes_number=5,
    #     num_workers=1,
    #     save_file_path_name="./results/logs-test.csv",
    #     num_unfinished_tasks=0,
    # )

    # check solver
    try:
        check_solver_and_upload(
            ecr_repo=ecr_repo,
            solver_name=worker_config_obj.solver.solver_name,
            saved_solver_bucket=worker_config_obj.solver.saved_solver_bucket,
            solver_lic_file_name=worker_config_obj.solver.solver_lic_file_name,
            solver_lic_local_path=worker_config_obj.solver.solver_lic_local_path,
            saved_temp_path_in_bucket=worker_config_obj.solver.saved_temp_path_in_bucket,
            aws_access_key=aws_config_obj.aws_access_key,
            aws_secret_access_key=aws_config_obj.aws_secret_access_key,
            aws_region=aws_config_obj.aws_region,
        )
    except Exception as e:
        logger.error(f"Upload Solver error:{e}")
        return

    # check if build images.
    if is_build_image:
        rollout = True  # build image always rollout sevices
        temp_image_tag = socket.gethostname()

        if is_docker:
            logger.info("========= Build images and run in docker ========")
            invoke_docker_compose_build_and_run()
        else:

            invoke_docker_compose_build()
            for service in services_config_list:
                # only inspect worker and server
                if service == "worker" or service == "server":
                    # Updated image tag
                    update_image = service
                    if not is_local:
                        update_image = f"{ecr_repo}/{service}"

                    invoke_tag_image(
                        origin_image=service,
                        update_image=update_image,
                        image_tag=temp_image_tag,
                    )
                    services_config_list[service]["image_tag"] = temp_image_tag

        if not is_local:
            try:
                validation_resp = invoke_ecr_validation(ecr_repo=ecr_repo)
                logger.info(validation_resp)
            except Exception as e:
                logger.error(f"Error :{e}")
                return
            push_thread = list()
            try:
                for service in services_config_list:
                    logger.info(
                        f" ============= Push image to {ecr_repo}/{service}:{temp_image_tag} =================="
                    )
                    x = threading.Thread(
                        target=invoke_push_image,
                        args=(service, temp_image_tag, ecr_repo),
                    )
                    x.name = service
                    push_thread.append(x)
                    x.start()
            except Exception as e:
                logger.error(f"{e}")
                return

            for index, thread in enumerate(push_thread):
                thread.join()
                logging.info("Wait push to %s thread done", thread.name)

    if is_docker:
        logger.info("Running docker")
        # Neither AWS of local environment, running servies in docker, we don't need to  take care of EKS.
    else:
        if is_local:
            logger.info("Running local kubernetes")
        else:
            logger.info("Running AWS kubernetes")
            if check_environment_is_aws() is not True:
                logger.error(
                    "Ruuning in local not AWS. Please use [-l] option command."
                )
                return
            # update aws eks
            invoke_eks_updagte_kubeconfig(cluster_name=aws_config_obj.cluster_name)
            try:
                scale_eks_nodes_and_wait(
                    scale_node_num=aws_config_obj.eks_nodes_number,
                    total_wait_time=aws_config_obj.scale_eks_nodes_wait_time,
                    delay=1,
                    cluster_name=aws_config_obj.cluster_name,
                    nodegroup_name=aws_config_obj.nodegroup_name,
                )
            except Exception as e:
                logger("Scale nodes error")

        # updae k8s
        # check worker deployment
        # loop k8s services list , create or update k8s depolyment and services
        for key, value in services_config_list.items():
            service_name = key
            deployment_file = value["deployment_file"]
            service_file = value["service_file"]
            desired_replicas = value["desired_replicas"]
            image_base_url = value["image_name"]
            image_tag = value["image_tag"]
            imagePullPolicy = value["imagePullPolicy"]

            # update deployment, if image tag or replicas are changed, update deployments
            create_or_update_k8s_deployment(
                service_name=service_name,
                image_tag=image_tag,
                image_base_url=image_base_url,
                imagePullPolicy=imagePullPolicy,
                desired_replicas=desired_replicas,
                k8s_file_name=deployment_file,
                rollout=rollout,
            )
            # service file exists
            if service_file:
                # check service exist
                if not check_k8s_services_exists(name=service_name):
                    logger.info(
                        f"========= Create {service_file} services =========== "
                    )
                    create_k8s_svc_from_yaml(full_path_name=service_file)

        # wait k8s pod  ready
        threads = list()
        try:
            for key, value in services_config_list.items():
                desired_replicas = value["desired_replicas"]
                x = threading.Thread(
                    target=wait_pod_ready,
                    args=(
                        desired_replicas,
                        key,
                        aws_config_obj.interval_of_wait_pod_ready,
                        1,
                    ),
                )
                x.name = key
                threads.append(x)
                x.start()
        except Exception as e:
            logger.error(f"{e}")
            return

        for index, thread in enumerate(threads):
            thread.join()
            logging.info("Wait %s thread done", thread.name)

    logger.info(" ========= Clean previous SQS ========= ")
    sqs_client = connect_aws_client(
        client_name="sqs",
        key_id=aws_config_obj.aws_access_key,
        secret=aws_config_obj.aws_secret_access_key,
        region=aws_config_obj.aws_region,
    )
    clean_user_previous_sqs_message(
        sqs_url=sqs_url,
        sqs_client=sqs_client,
        wait_time=2,
        counter=60,
        delay=1,
        user_id=worker_config_obj.user_id,
    )
    # check server ready and return running server name.

    ready_server_name = checck_server_ready_and_get_name(
        deployment_services_list=services_config_list,
        is_docker=is_docker,
    )
    if ready_server_name is None:
        logger.error("Cannot get server name")
        return
    logger.info(f"------ {ready_server_name}")
    # send command to server and get task IDs
    worker_replicas = 0
    for key, value in services_config_list.items():
        if key == "worker":
            worker_replicas = value["desired_replicas"]
    logger.info(f"Current worker replica:{worker_replicas}")
    if worker_replicas == 0:
        logger.error(f"Number of worker error:{worker_replicas} ")

    initial_process_time = time.time() - start_time

    proces = list()
    try:
        logger.info(
            "============ Running invoke process files commmand in multiprocess ==========="
        )
        proc_x = Process(
            target=send_command_to_server(
                server_name=ready_server_name,
                number=number,
                worker_config_json=config_json["worker_config"],
                is_docker=is_docker,
                num_file_to_process_per_round=worker_replicas * 3,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region,
                sns_topic=sns_topic,
            )
        )
        proc_x.name = "Invoker process files"
        proc_x.start()
    except Exception as e:
        logger.error(f"Invoke process files in server error:{e}")
        return
    # try:
    #     logger.info(" ========= Long pulling SQS in multiprocess========= ")
    #     acccepted_idle_time = int(worker_config_obj.acccepted_idle_time)
    #     delay = aws_config_obj.interval_of_check_dynamodb_in_second
    #     proces_y = Process(
    #         target=long_pulling_sqs(
    #             wait_time=7200,
    #             delay=delay,
    #             sqs_url=sqs_url,
    #             worker_config=worker_config_obj,
    #             acccepted_idle_time=acccepted_idle_time,
    #             aws_access_key=aws_access_key,
    #             aws_secret_access_key=aws_secret_access_key,
    #             aws_region=aws_region,
    #         )
    #     )

    #     proces_y.name = "Long pulling"
    #     proces.append(proces_y)
    #     proces_y.start()
    # except Exception as e:
    #     logger.error(f"Long pulling sqs thread error:{e}")
    #     return
    # for index, proc in enumerate(proces):
    #     proc.join()
    #     logging.info("%s proc done", proc.name)
    delay = aws_config_obj.interval_of_check_dynamodb_in_second
    acccepted_idle_time = int(worker_config_obj.acccepted_idle_time)
    unfinished_tasks_id_set = long_pulling_sqs(
        wait_time=7200,
        delay=delay,
        sqs_url=sqs_url,
        worker_config=worker_config_obj,
        acccepted_idle_time=acccepted_idle_time,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
    )
    logger.info(" ----- init end services process --------- ")
    total_process_time = time.time() - start_time
    num_unfinished_tasks = len(unfinished_tasks_id_set)
    initial_end_services(
        worker_config=worker_config_obj,
        is_docker=is_docker,
        delete_nodes_after_processing=delete_nodes,
        is_build_image=is_build_image,
        services_config_list=services_config_list,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
        scale_eks_nodes_wait_time=config_json["aws_config"][
            "scale_eks_nodes_wait_time"
        ],
        cluster_name=config_json["aws_config"]["cluster_name"],
        nodegroup_name=config_json["aws_config"]["nodegroup_name"],
        initial_process_time=float(initial_process_time),
        total_process_time=float(total_process_time),
        eks_nodes_number=aws_config_obj.eks_nodes_number,
        num_workers=services_config_list["worker"]["desired_replicas"],
        num_unfinished_tasks=num_unfinished_tasks,
        instanceType=config_json["aws_config"]["instanceType"],
    )

    print(" ======== Completed ========== ")
    return
