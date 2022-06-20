from http import server
import socket
import threading
import click
from os.path import exists
import logging
import os
import json

import modules
from server.models.Configurations import (
    make_config_obj_from_yaml,
    convert_yaml_to_json,
    AWS_CONFIG,
    WORKER_CONFIG,
)
from server.utils.aws_utils import (
    check_aws_validity,
    connect_aws_client,
    check_environment_is_aws,
)

from modules.utils.task_thread import (
    long_pulling_sqs,
)


from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("aws_access_key")
AWS_SECRET_ACCESS_KEY = os.getenv("aws_secret_key")
AWS_DEFAULT_REGION = os.getenv("aws_region")
SQS_URL = os.getenv("SQS_URL")  # aws standard url
SNS_TOPIC = os.getenv("SNS_TOPIC")  # aws sns
DLQ_URL = os.getenv("DLQ_URL")  # dead letter queue url
ECR_REPO = os.getenv("ECR_REPO")  # get ecr repo

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


# Parent Command
@click.group()
def main():
    pass


# ***************************
#  Run files
# ***************************


@main.command()
@click.option(
    "--number",
    "-n",
    help="""
    Process the first n files in the defined bucket of config.yaml.
    If number is None, this application process defined files in config.yaml.
    If number is 0, this application processs all files in the defined bucket in config.yaml.
    If number is an integer, this applicaion process the first `number` files in the defined bucket in config.yaml.
    """,
    default=None,
)
@click.option(
    "--deletenodes",
    "-d",
    is_flag=True,
    help="Enable deleting eks node after complete this application. Default value is False.",
)
@click.option(
    "--configfile",
    "-f",
    help="Assign custom config files, Default files name is ./config/config.yaml",
    default="config.yaml",
)
@click.option(
    "--rollout",
    "-r",
    is_flag=True,
    help="Enable deleting current k8s deployment services and re-deployment services. Default value is False",
)
@click.option(
    "--imagetag",
    "-i",
    help="Specifiy the image tag. Default value is 'latest'",
    default="latest",
)
@click.option(
    "--docker",
    "-do",
    is_flag=True,
    help="Default value is False. If it is True, the services run in docker environment.Otherwise, the services run in k8s environment.",
)
@click.option(
    "--local",
    "-l",
    is_flag=True,
    help="Default value is False. If it is True, define running environemnt in local.Otherwiser, define running environemt on AWS",
)
@click.option(
    "--build",
    "-b",
    is_flag=True,
    help="Build a temp image and use it. If on AWS k8s environment, \
    build and push image to ECR with temp image tag. These images will be deleted after used.\
    If you would like to preserve images, please use build-image command instead ",
)
def run_files(
    number: int = 1,
    deletenodes: bool = False,
    configfile: str = None,
    rollout: str = False,
    imagetag: str = "latest",
    docker: bool = False,
    local: bool = False,
    build: bool = False,
):
    """
    Proccess files in defined bucket
    :param number:      number of first n files in bucket. Default value is `None`.
                        If number is None, this application process defined files in config.yaml.
                        If number is 0, this application processs all files in the defined bucket in config.yaml.
                        If number is an integer, this applicaion process the first `number` files in the defined bucket in config.yaml.
    :param deletenodes: Enable deleting eks node after complete this application. Default value is False.
    :param configfile:  Define config file name. Default value is "./config/config.yaml"
    :param rollout:     Enable delete current k8s deployment and re-deployment. Default value is False
    :param imagetag:    Specifiy the image tag. Default value is 'latest'
    :param docker:      Default value is False. If it is True, the services run in docker environment.
                        Otherwise, the services run in k8s environment.
    :param local:       Default value is False. If it is True, define running environemnt in local.
                        Otherwiser, define running environemt on AWS
    :param build:       Build a temp image and use it. If on AWS k8s environment, \
                        build and push image to ECR with temp image tag. These images will be deleted after used.\
                        If you would like to preserve images, please use build-image command instead
    """
    run_process_files(
        number=number,
        delete_nodes=deletenodes,
        configfile=configfile,
        rollout=rollout,
        image_tag=imagetag,
        is_docker=docker,
        is_local=local,
        is_build_image=build,
    )


# ***************************
#  Scale the eks nodes' number
# ***************************


@main.command()
@click.argument("min_nodes")
@click.option(
    "--configfile",
    "-f",
    help="Assign config files, Default files is config.yaml under /config",
    default="config.yaml",
)
def nodes_scale(min_nodes, configfile):
    """Increate or decrease nodes number"""
    logger.info(f"Scale nodes {min_nodes} {configfile}")
    # check aws credential
    try:
        check_aws_validity(key_id=AWS_ACCESS_KEY_ID, secret=AWS_SECRET_ACCESS_KEY)
    except Exception as e:
        logger.error(f"AWS credential failed: {e}")
        return

    # check config exist
    config_yaml = f"./config/{configfile}"

    if exists(config_yaml) is False:
        logger.warning(
            f"./config/{configfile} not exist, use default config.yaml instead"
        )
        config_yaml = f"./config/config.yaml"

    config_json = convert_yaml_to_json(yaml_file=config_yaml)
    aws_config_obj = AWS_CONFIG(config_json["aws_config"])
    aws_config_obj.aws_access_key = AWS_ACCESS_KEY_ID
    aws_config_obj.aws_secret_access_key = AWS_SECRET_ACCESS_KEY
    aws_config_obj.aws_region = AWS_DEFAULT_REGION
    aws_config_obj.sns_topic = SNS_TOPIC
    aws_config_obj.sqs_url = SQS_URL
    aws_config_obj.dlq_url = DLQ_URL
    aws_config_obj.ecr_repo = ECR_REPO

    # worker_config_obj = WORKER_CONFIG(config_json["worker_config"])
    modules.eks_utils.scale_eks_nodes_and_wait(
        scale_node_num=int(min_nodes),
        total_wait_time=aws_config_obj.scale_eks_nodes_wait_time,
        delay=1,
        cluster_name=aws_config_obj.cluster_name,
        nodegroup_name=aws_config_obj.nodegroup_name,
    )


# ***************************
#  Check eks node status
# ***************************


@main.command()
def check_nodes():
    """Check nodes status"""
    modules.command_utils.check_nodes_status()


# ***************************
#  build and push image status
# ***************************


@main.command()
@click.option(
    "--tag",
    "-t",
    help="Rollout and restart of webapp and worker pod of kubernetes",
    default="latest",
)
@click.option(
    "--push",
    "-p",
    is_flag=True,
    help="Is push image to ecr : Default is False",
)
def build_images(tag: str = None, push: bool = False):
    """Build image from docker-compose and push to ECR"""
    click.echo(f"Build image :{tag}")
    build_resp = modules.utils.invoke_docker_compose_build()
    # click.echo(build_resp)
    services_list = ["worker", "server"]
    try:
        for service in services_list:
            click.echo(f"tag {ECR_REPO}/{service}:{tag}")
            tag_worker = modules.utils.invoke_tag_image(
                image_name=service,
                image_tag=tag,
                ecr_repo=ECR_REPO,
            )
    except Exception as e:
        logger.error("Tag image error")
        return

    if push:
        if tag == "latest" or tag == "develop":
            click.echo("======================= Error ========================\n")
            click.echo(f"{service}:{tag} pushed failed. \n")
            click.echo("It has to be push through Github Action CI/CD pipeline\n")
            click.echo("======================================================\n")
            return

        validation_resp = modules.utils.invoke_ecr_validation()
        click.echo(validation_resp)
        try:
            for service in services_list:
                click.echo(f"push {ECR_REPO}/{service}:{tag}")
                push_worker = modules.utils.invoke_push_image(
                    image_name=service, image_tag=tag, ecr_repo=ECR_REPO
                )
        except Exception as e:
            logger.error("Push image error")
            return


# ***************************
#  Read process logs file
#  in S3 buckeet, and save gantt
#  plot locally
# ***************************


@main.command()
@click.option(
    "--configfile",
    "-f",
    help="Assign custom config files, Default files name is ./config/config.yaml",
    default="config.yaml",
)
def processlogs(configfile):
    """Porcess logs.csv file on AWS"""
    # try:
    #      = make_config_obj_from_yaml(
    #         yaml_file="./config/config.yaml",
    #         aws_access_key=AWS_ACCESS_KEY_ID,
    #         aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    #         aws_region=AWS_DEFAULT_REGION,
    #         sns_topic=SNS_TOPIC,
    #     )

    # except Exception as e:
    #     logger.error(f"Convert yaml  error:{e}")
    #     return
    # modules.command_utils.process_logs_and_plot(config_params_obj=config_params_obj)
    try:
        check_aws_validity(key_id=AWS_ACCESS_KEY_ID, secret=AWS_SECRET_ACCESS_KEY)
    except Exception as e:
        logger.error(f"AWS credential failed: {e}")
        return

    # check config exist
    config_yaml = f"./config/{configfile}"

    if exists(config_yaml) is False:
        logger.warning(
            f"./config/{configfile} not exist, use default config.yaml instead"
        )
        config_yaml = f"./config/config.yaml"

    config_json = convert_yaml_to_json(yaml_file=config_yaml)
    aws_config_obj = AWS_CONFIG(config_json["aws_config"])
    aws_config_obj.aws_access_key = AWS_ACCESS_KEY_ID
    aws_config_obj.aws_secret_access_key = AWS_SECRET_ACCESS_KEY
    aws_config_obj.aws_region = AWS_DEFAULT_REGION
    aws_config_obj.sns_topic = SNS_TOPIC
    aws_config_obj.sqs_url = SQS_URL
    aws_config_obj.dlq_url = DLQ_URL
    aws_config_obj.ecr_repo = ECR_REPO

    worker_config_obj = WORKER_CONFIG(config_json["worker_config"])

    logs_file_path_name = (
        worker_config_obj.saved_logs_target_path
        + "/"
        + worker_config_obj.saved_logs_target_filename
    )
    saved_file_name = (
        worker_config_obj.saved_target_path
        + "/"
        + worker_config_obj.saved_target_filename
    )
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=AWS_ACCESS_KEY_ID,
        secret=AWS_SECRET_ACCESS_KEY,
        region=AWS_DEFAULT_REGION,
    )
    modules.command_utils.get_saved_data_from_logs(
        logs_file_path_name=logs_file_path_name,
        s3_client=s3_client,
        saved_file_name=saved_file_name,
        bucket=worker_config_obj.saved_bucket,
    )


@main.command()
def get_iam():
    click.echo("get iam ")
    # iam_client = connect_aws_client("iam")
    # response = {"Subject":"SAVED_DATA", "Messages":{"ssda":"sdas2s"}}
    # response['Messages']['test'] = 2
    # print(response)


# ***************************
#  Read DLQ
# ***************************


@main.command()
@click.option("--empty", "-e", is_flag=True, help=" Empty DLQ after receive message")
def read_dlq(empty):
    """Read messages from dlq"""
    click.echo(f"Read DLQ from :{DLQ_URL}. Delete message: {empty}")
    modules.command_utils.print_dlq(
        delete_messages=empty,
        aws_key=AWS_ACCESS_KEY_ID,
        aws_secret_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        dlq_url=DLQ_URL,
        wait_time=80,
        delay=0.5,
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
    :param is_local:    Default value is False. If it is True, define running environemnt in local.
                        Otherwiser, define running environemt on AWS
    :param is_build_image:    Build a temp image and use it. If on AWS k8s environment, \
                        build and push image to ECR with temp image tag. These images will be deleted after used.\
                        If you would like to preserve images, please use build-image command instead
    """
    # check aws credential
    try:
        check_aws_validity(key_id=AWS_ACCESS_KEY_ID, secret=AWS_SECRET_ACCESS_KEY)
    except Exception as e:
        logger.error(f"AWS credential failed: {e}")
        return

    # check config exist
    config_yaml = f"./config/{configfile}"

    if exists(config_yaml) is False:
        logger.warning(
            f"./config/{configfile} not exist, use default config.yaml instead"
        )
        config_yaml = f"./config/config.yaml"

    config_json = convert_yaml_to_json(yaml_file=config_yaml)
    aws_config_obj = AWS_CONFIG(config_json["aws_config"])
    aws_config_obj.aws_access_key = AWS_ACCESS_KEY_ID
    aws_config_obj.aws_secret_access_key = AWS_SECRET_ACCESS_KEY
    aws_config_obj.aws_region = AWS_DEFAULT_REGION
    aws_config_obj.sns_topic = SNS_TOPIC
    aws_config_obj.sqs_url = SQS_URL
    aws_config_obj.dlq_url = DLQ_URL
    aws_config_obj.ecr_repo = ECR_REPO

    worker_config_obj = WORKER_CONFIG(config_json["worker_config"])

    services_config_list = config_json["services_config_list"]
    ecr_client = connect_aws_client(
        client_name="ecr",
        key_id=AWS_ACCESS_KEY_ID,
        secret=AWS_SECRET_ACCESS_KEY,
        region=AWS_DEFAULT_REGION,
    )
    #  check environments , check image name and tag exist. Update images name and tag to object
    services_config_list = (
        modules.command_utils.update_config_json_image_name_and_tag_base_on_env(
            is_local=is_local,
            image_tag=image_tag,
            ecr_client=ecr_client,
            ecr_repo=ECR_REPO,
            services_config_list=services_config_list,
        )
    )

    # check solver
    try:
        modules.command_utils.check_solver_and_upload(
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
            modules.invoke_function.invoke_docker_compose_build_and_run()
        else:
            logger.info("========= Build image ========")
            modules.utils.invoke_docker_compose_build()
            logger.info(f"========= tag image {temp_image_tag} ========")
            for service in services_config_list:
                # only inspect worker and server
                if service == "worker" or service == "server":
                    # Updated image tag
                    update_image = service
                    if not is_local:
                        update_image = f"{ECR_REPO}/{service}"

                    modules.utils.invoke_tag_image(
                        origin_image=service,
                        update_image=update_image,
                        image_tag=temp_image_tag,
                    )
                    services_config_list[service]["image_tag"] = temp_image_tag

        if not is_local:
            try:
                validation_resp = modules.utils.invoke_ecr_validation()
                logger.info(validation_resp)
            except Exception as e:
                logger.error(f"Error :{e}")
                return
            push_thread = list()
            try:
                for service in services_config_list:
                    x = threading.Thread(
                        target=modules.utils.invoke_push_image,
                        args=(service, temp_image_tag, ECR_REPO),
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
            modules.invoke_function.invoke_eks_updagte_kubeconfig(
                cluster_name=aws_config_obj.cluster_name
            )
            modules.eks_utils.scale_eks_nodes_and_wait(
                scale_node_num=aws_config_obj.eks_nodes_number,
                total_wait_time=aws_config_obj.scale_eks_nodes_wait_time,
                delay=1,
                cluster_name=aws_config_obj.cluster_name,
                nodegroup_name=aws_config_obj.nodegroup_name,
            )
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
            modules.command_utils.create_or_update_k8s_deployment(
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
                if not modules.utils.k8s_utils.check_k8s_services_exists(
                    name=service_name
                ):
                    logger.info(f"========= Create services{service_file} =========== ")
                    modules.utils.k8s_utils.create_k8s_svc_from_yaml(
                        full_path_name=service_file
                    )

        # wait k8s pod  ready
        threads = list()
        try:
            for key, value in services_config_list.items():
                desired_replicas = value["desired_replicas"]
                x = threading.Thread(
                    target=modules.utils.eks_utils.wait_pod_ready,
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

    # # clear sqs
    logger.info(" ========= Clean previous SQS ========= ")
    sqs_client = connect_aws_client(
        client_name="sqs",
        key_id=aws_config_obj.aws_access_key,
        secret=aws_config_obj.aws_secret_access_key,
        region=aws_config_obj.aws_region,
    )
    modules.sqs.clean_previous_sqs_message(
        sqs_url=SQS_URL, sqs_client=sqs_client, wait_time=2, counter=60, delay=1
    )
    # start receive SNS message
    # waiting to receive sns message

    # send command to server and process files command.
    total_task_num = modules.command_utils.get_total_task_number(
        number=number,
        aws_config=aws_config_obj,
        worker_config_json=config_json["worker_config"],
    )
    logger.info(f"total_task_num {total_task_num}")
    # waiting to receive sns message
    threads = list()
    worker_replicas = 1
    for key, value in services_config_list.items():
        if key == "worker":
            worker_replicas = value["desired_replicas"]
            # logger.info(f"worker_replicas :{worker_replicas}")
    looping_wait_time = int(
        (aws_config_obj.interval_of_total_wait_time_of_sqs)
        * (total_task_num)
        / worker_replicas
    )
    threads = list()
    try:
        x = threading.Thread(
            target=modules.command_utils.invoke_process_files_based_on_number(
                number=number,
                aws_config=aws_config_obj,
                worker_config_json=config_json["worker_config"],
                deployment_services_list=services_config_list,
                is_docker=is_docker,
            )
        )
        y = threading.Thread(
            target=long_pulling_sqs(
                wait_time=looping_wait_time,
                delay=aws_config_obj.interval_of_check_sqs_in_second,
                sqs_url=SQS_URL,
                num_task=total_task_num,
                worker_config=worker_config_obj,
                aws_config=aws_config_obj,
                delete_nodes_after_processing=delete_nodes,
                is_docker=is_docker,
                dlq_url=DLQ_URL,
            )
        )
        x.name = "Invoker process files"
        y.name = "Long pulling"
        threads.append(x)
        threads.append(y)
        x.start()
        y.start()
    except Exception as e:
        logger.error(e)

    for index, thread in enumerate(threads):
        thread.join()
        logging.info("%s thread done", thread.name)
    logger.info(" ----- init end services process --------- ")
    modules.command_utils.initial_end_services(
        worker_config=worker_config_obj,
        aws_config=aws_config_obj,
        is_docker=is_docker,
        is_local=is_local,
        delete_nodes_after_processing=delete_nodes,
        is_build_image=is_build_image,
        services_config_list=services_config_list,
    )
    logger.info("=========== Completed ==========")

    return


if __name__ == "__main__":
    main()
