from os import system
import time
import os
from os.path import exists

from .command_utils import (
    check_solver_and_upload,
    update_config_json_image_name_and_tag_base_on_env,
    create_or_update_k8s_deployment,
    checck_server_ready_and_get_name,
    send_command_to_server,
)
from .initial_end_services import initial_end_services,process_local_logs_and_upload_s3

from .process_log import analyze_all_local_logs_files
import re

from .long_pulling_sqs import long_pulling_sqs
from .AWS_CONFIG import AWS_CONFIG
from .WORKER_CONFIG import WORKER_CONFIG
from .check_aws import connect_aws_client, check_environment_is_aws,connect_aws_resource

from .modiy_config_parameters import modiy_config_parameters, convert_yaml_to_json
import logging
import socket
import threading
from .invoke_function import (
    invoke_docker_compose_up,
    invoke_docker_compose_build,
    invoke_tag_image,
    invoke_ecr_validation,
    invoke_push_image,
    invoke_eks_updagte_kubeconfig,
)
from .k8s_utils import check_k8s_services_exists, create_k8s_svc_from_yaml

from .eks_utils import scale_eks_nodes_and_wait, wait_pod_ready

from .sqs import clean_user_previous_sqs_message,send_queue_message,receive_queue_message, create_queue,delete_queue,list_queues
from multiprocessing.dummy import Process

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
    # sqs_url: str = None,
    sns_topic: str = None,
    dlq_url: str = None,
    ecr_repo: str = None,
    repeatnumber:int = 1,
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
    :param repeatnumber:  number of repeat time of run-files function
    """
    # check aws credential
   
    # remove all files in results 
    # list all files in results folder
    # check config exist



    config_yaml = f"./config/{configfile}"

    if exists(config_yaml) is False:
        logger.warning(
            f"./config/{configfile} not exist, use default config.yaml instead"
        )
        config_yaml = f"./config/config.yaml"

    _config_json = convert_yaml_to_json(yaml_file=config_yaml)
    # print(_config_json["worker_config"]["save_performance_local"])
    # analyze_all_local_logs_files(
    #     instanceType="test",
    #     logs_file_path=_config_json["worker_config"]["saved_path_local"],
    #     initial_process_time=0,
    #     total_process_time=1010,
    #     eks_nodes_number=1,
    #     num_workers=1,
    #     save_file_path_name=_config_json["worker_config"]["save_performance_local"],
    #     num_unfinished_tasks=0,
    #     code_templates_folder=_config_json["worker_config"]["code_template_folder"],
    #     repeat_number =repeatnumber,
    # )
    # return
    result_local_folder = _config_json["worker_config"]["saved_path_local"]
    if os.path.isdir(result_local_folder) is False:
        logger.info(f"Create local {result_local_folder} path")
        os.mkdir(result_local_folder)
    # # list all files in folder:
    # glmfiles = []
    for _file in os.listdir(result_local_folder):
        _full_file = f"{result_local_folder}/{_file}"
        os.remove(_full_file)
        logger.info(f"remove {_full_file}")
        
    current_repeat_number = 0 



    init_process_time_list = []
    total_proscee_time_list = []
    sqs_resource = connect_aws_resource(
            resource_name='sqs',
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
    )
   
    host_name = (socket.gethostname())
    user_id = re.sub('[^a-zA-Z0-9]', '', host_name)
    sqs_name = f"gcd-{user_id}"

    # create_sqs_if_not_exist(sqs_resource=sqs_resource, queue_name=sqs_name)
    
    # sqs_client = connect_aws_client(
    #         client_name='sqs',
    #         key_id=aws_access_key,
    #         secret=aws_secret_access_key,
    #         region=aws_region,
    # )

    # queue_list = list_queues(sqs_resource = sqs_resource)
    # print(queue_list)
    # try:
    #     queue = sqs_client.get_queue_url(QueueName=sqs_name)
    #     sqs_url=queue['QueueUrl']
    #     print(queue)
    # except Exception as e:
    
    #     print("---------")
    #     print(e)
    # print("---------")
    # print(queue)
    # print(sqs_url)

    # return
    
    try:
        create_res = create_queue(
            queue_name=sqs_name,
            delay_seconds="0",
            visiblity_timeout="60",
            sqs_resource=sqs_resource
        )
       
        sqs_url = create_res.url
        logger.info(f"======== Create {sqs_url} success =======")
    except Exception as e:
        logger.error(f"Fail to create sqs: {e}")
        return

    # return
    # time.sleep(60)
    # sqs_client = connect_aws_client(
    #         client_name='sqs',
    #         key_id=aws_access_key,
    #         secret=aws_secret_access_key,
    #         region=aws_region,
    # )
    # res = delete_queue(
    #     queue_name=sqs_url,
    #     sqs_client=sqs_client
    # )
    # print("-----------")
    # print(res)
    # time.sleep(60)


    while current_repeat_number < repeatnumber:
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
            current_repeat_number = current_repeat_number,
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
                logger.info(f"========= Build images and run in docker ======== {worker_config_obj.code_template_folder}")
                # invoke_docker_compose_build_and_run()
                invoke_docker_compose_build(
                worker_folder=config_json['worker_config']['worker_dockerfile_folder'], code_template_folder=worker_config_obj.code_template_folder
                )
                invoke_docker_compose_up()
            else:
                logger.info(f" ========= Build images and run in k8s ======== {worker_config_obj.code_template_folder}")
                invoke_docker_compose_build(
                    worker_folder=config_json['worker_config']['worker_dockerfile_folder'],code_template_folder=worker_config_obj.code_template_folder
                )
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
                    sqs_url=sqs_url,
                )
            )
            proc_x.name = "Invoker process files"
            initial_process_time = time.time() - start_time
            proc_x.start()
        except Exception as e:
            logger.error(f"Invoke process files in server error:{e}")
            return

        
        delay = aws_config_obj.interval_of_check_dynamodb_in_second
        acccepted_idle_time = int(worker_config_obj.acccepted_idle_time)
        unfinished_tasks_id_set = long_pulling_sqs(
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

        init_process_time_list.append(round(initial_process_time,2))
        total_proscee_time_list.append(round(total_process_time,2)) 
        process_local_logs_and_upload_s3(
            worker_config=worker_config_obj,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
  
        current_repeat_number += 1
        print(f" ======== Completed  {current_repeat_number}, Total repeat:{repeatnumber} ========== ")

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
            sqs_url= sqs_url
        )
    analyze_all_local_logs_files(
        instanceType=config_json["aws_config"]["instanceType"],
        logs_file_path=config_json["worker_config"]["saved_path_local"],
        init_process_time_list=init_process_time_list,
        total_proscee_time_list=total_proscee_time_list,
        eks_nodes_number=aws_config_obj.eks_nodes_number,
        num_workers=services_config_list["worker"]["desired_replicas"],
        save_file_path_name=config_json["worker_config"]["save_performance_local"],
        num_unfinished_tasks=0,
        code_templates_folder=config_json["worker_config"]["code_template_folder"],
        repeat_number =repeatnumber,
    )
    print("End of analyzing logs")
    
    return
