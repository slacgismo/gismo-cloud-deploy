from concurrent.futures import thread
from http import server
import re
import threading
from unicodedata import name
from urllib import response
import click
from os.path import exists
import logging
import os

from server.utils.aws_utils import check_ecr_tag_exists
import modules
from server.models.Configurations import make_config_obj_from_yaml
from server.utils.aws_utils import (
    check_aws_validity,
    connect_aws_client,
    check_environment_is_aws,
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
def run_files(number, deletenodes, configfile, rollout, imagetag, docker, local):
    """Run Process Files"""
    run_process_files(
        number=number,
        delete_nodes=deletenodes,
        configfile=configfile,
        rollout=rollout,
        image_tag=imagetag,
        is_docker=docker,
        is_local=local,
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
    try:
        # config_obj = import_config_from_yaml(configfile)
        config_params_obj = make_config_obj_from_yaml(
            yaml_file=f"./config/{configfile}",
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            sns_topic=SNS_TOPIC,
        )

    except Exception as e:
        return logger.error(e)
    modules.eks_utils.scale_nodes_and_wait(
        scale_node_num=min_nodes,
        counter=int(config_params_obj.scale_eks_nodes_wait_time),
        delay=1,
        config_params_obj=config_params_obj,
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
    # build_resp = modules.utils.invoke_docker_compose_build()
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
#  check k8s image tag and
#  re-deployment
# ***************************
@main.command()
@click.option(
    "--tag",
    "-t",
    help="Rollout and restart of webapp and worker pod of kubernetes",
    default="latest",
)
@click.option(
    "--local",
    "-l",
    is_flag=True,
    help="Is environment local or aws. Default is False (= AWS) (True = local)",
)
@click.option(
    "--configfile",
    "-f",
    help="Assign config files, Default files is config.yaml under /config",
    default="config.yaml",
)
@click.option(
    "--rollout",
    "-r",
    is_flag=True,
    help="Rollout and restart of webapp and worker pod of kubernetes",
)
def k8s_deploy(tag: str, local: bool, configfile: str, rollout: bool):
    """Deploy k8s services"""
    click.echo(
        f"Select image tag: {tag}, Is environment AWS:{not local}, config file: {configfile}, rollout: {rollout}"
    )
    run_k8s_deploy(
        image_tag=tag, is_local_environem=local, configfile=configfile, rollout=rollout
    )


# ***************************
#  Read process logs file
#  in S3 buckeet, and save gantt
#  plot locally
# ***************************


@main.command()
def processlogs():
    """Porcess logs.csv file on AWS"""
    try:
        config_params_obj = make_config_obj_from_yaml(
            yaml_file="./config/config.yaml",
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            sns_topic=SNS_TOPIC,
        )

    except Exception as e:
        logger.error(f"Convert yaml  error:{e}")
        return
    modules.command_utils.process_logs_and_plot(config_params_obj=config_params_obj)


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


def run_k8s_deploy(
    image_tag: str, is_local_environem: bool, configfile: str, rollout: bool
) -> None:

    # 1. convert yaml to configure obj
    # 2. check environment
    # 3. chcek if k8s exist, check tag
    # 1.1 if tag is not correct, delete current deployment, apply new image
    # 4. if tag is correct. check replicas
    # 2.1. if replicas is not correct , attached new replicas
    # 5. wait pod ready with correct replicas

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

    try:
        config_params_obj = make_config_obj_from_yaml(
            yaml_file=config_yaml,
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            sns_topic=SNS_TOPIC,
        )

    except Exception as e:
        logger.error(f"Convert yaml  error:{e}")
        return

    if is_local_environem is False:
        logger.info("Running on AWS")
        # wait eks node status
        worker_image_base_url = f"{ECR_REPO}/worker"
        server_image_base_url = f"{ECR_REPO}/server"
        # check ecr image exist

        ecr_client = connect_aws_client(
            client_name="ecr",
            key_id=config_params_obj.aws_access_key,
            secret=config_params_obj.aws_secret_access_key,
            region=config_params_obj.aws_region,
        )
        # check ecr tag exists
        if (
            check_ecr_tag_exists(
                image_tag=image_tag, repoNme="worker", ecr_client=ecr_client
            )
            is False
        ):
            logger.error(f"{worker_image_url} does not exist")
            return

        if (
            check_ecr_tag_exists(
                image_tag=image_tag, repoNme="server", ecr_client=ecr_client
            )
            is False
        ):
            logger.error(f"{server_image_url} does not exist")
            return

        # update image tag
        config_params_obj.deployment_services_list["worker"][
            "image_name"
        ] = worker_image_base_url
        config_params_obj.deployment_services_list["server"][
            "image_name"
        ] = server_image_base_url
        # update image url
        config_params_obj.deployment_services_list["worker"]["image_tag"] = image_tag
        config_params_obj.deployment_services_list["server"]["image_tag"] = image_tag

        # wait eks node:
        modules.utils.eks_utils.scale_nodes_and_wait(
            scale_node_num=int(config_params_obj.eks_nodes_number),
            counter=int(config_params_obj.scale_eks_nodes_wait_time),
            delay=1,
            config_params_obj=config_params_obj,
        )
    else:
        logger.info("Running in Local")
        worker_image_url = f"worker:{image_tag}"
        server_image_url = f"server:{image_tag}"
        imagePullPolicy = "IfNotPresent"
        # check image exist
        try:
            modules.utils.invoke_docker_check_image_exist(image_name=worker_image_url)
            modules.utils.invoke_docker_check_image_exist(image_name=server_image_url)
        except Exception as e:
            logger.error(f"{worker_image_url} or {server_image_url} is not exist")
            return
        # update image worker and server tag
        config_params_obj.deployment_services_list["worker"]["image_tag"] = image_tag
        config_params_obj.deployment_services_list["server"]["image_tag"] = image_tag

    services_list = config_params_obj.deployment_services_list
    # check worker deployment
    # loop k8s services list , create or update k8s depolyment and services

    for key, value in services_list.items():
        service_name = key
        deployment_file = value["deployment_file"]
        service_file = value["service_file"]
        desired_replicas = value["desired_replicas"]
        image_base_url = value["image_name"]
        image_tag = value["image_tag"]
        # update deployment, if image tag or replicas are changed, update deployments
        modules.command_utils.create_or_update_k8s_deployment(
            service_name=service_name,
            image_base_url=image_base_url,
            image_tag=image_tag,
            imagePullPolicy=imagePullPolicy,
            desired_replicas=desired_replicas,
            k8s_file_name=deployment_file,
            rollout=rollout,
        )
        # service exists
        if service_file:
            # check service exist
            if not modules.utils.k8s_utils.check_k8s_services_exists(name=service_name):
                logger.info(f"========= Create services{service_file} =========== ")
                modules.utils.k8s_utils.create_k8s_svc_from_yaml(
                    full_path_name=service_file
                )

    # wait pod ready
    threads = list()
    try:
        for key, value in services_list.items():
            desired_replicas = value["desired_replicas"]
            x = threading.Thread(
                target=modules.utils.eks_utils.wait_pod_ready,
                args=(desired_replicas, key, 60, 1),
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

    return


def run_process_files(
    number: int = 1,
    delete_nodes: bool = False,
    configfile: str = None,
    rollout: bool = False,
    image_tag: str = None,
    is_docker: bool = False,
    is_local: bool = False,
) -> None:
    """
    Proccess files in S3 bucket
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

    try:
        config_params_obj_origin = make_config_obj_from_yaml(
            yaml_file=config_yaml,
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            sns_topic=SNS_TOPIC,
        )

    except Exception as e:
        logger.error(f"Convert yaml  error:{e}")
        return

    # update image tags
    ecr_client = connect_aws_client(
        client_name="ecr",
        key_id=config_params_obj_origin.aws_access_key,
        secret=config_params_obj_origin.aws_secret_access_key,
        region=config_params_obj_origin.aws_region,
    )
    # check environments , check image name and tag exist. Update images name and tag to object
    try:
        config_params_obj = modules.utils.command_utils.update_config_obj_image_name_and_tag_according_to_env(
            is_local=is_local,
            image_tag=image_tag,
            ecr_repo=ECR_REPO,
            ecr_client=ecr_client,
            config_params_obj=config_params_obj_origin,
        )
    except Exception as e:
        logger.error(f"{e}")
        return
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
            modules.utils.eks_utils.scale_nodes_and_wait(
                scale_node_num=int(config_params_obj.eks_nodes_number),
                counter=int(config_params_obj.scale_eks_nodes_wait_time),
                delay=1,
                config_params_obj=config_params_obj,
            )
        # updae k8s
        services_list = config_params_obj.deployment_services_list
        # check worker deployment
        # loop k8s services list , create or update k8s depolyment and services

        for key, value in services_list.items():
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
            # service exists
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
            for key, value in services_list.items():
                desired_replicas = value["desired_replicas"]
                x = threading.Thread(
                    target=modules.utils.eks_utils.wait_pod_ready,
                    args=(
                        desired_replicas,
                        key,
                        config_params_obj.interval_of__wait_pod_ready,
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

    # clear sqs
    logger.info(" ========= Clean previous SQS ========= ")
    sqs_client = connect_aws_client(
        client_name="sqs",
        key_id=config_params_obj.aws_access_key,
        secret=config_params_obj.aws_secret_access_key,
        region=config_params_obj.aws_region,
    )
    modules.sqs.clean_previous_sqs_message(
        sqs_url=SQS_URL, sqs_client=sqs_client, wait_time=2, counter=60, delay=1
    )

    try:
        total_task_num = modules.command_utils.invoke_process_files_based_on_number(
            number=number,
            config_params_obj=config_params_obj,
            config_yaml=config_yaml,
            is_docker=is_docker,
        )

    except Exception as e:
        logger.error(f"Invoke process files error:{e}")
        return
    thread = modules.TaskThread(
        threadID=1,
        name="sqs",
        counter=config_params_obj.interval_of_total_wait_time_of_sqs,
        wait_time=config_params_obj.interval_of_check_sqs_in_second,
        sqs_url=SQS_URL,
        num_task=total_task_num,
        config_params_obj=config_params_obj,
        delete_nodes_after_processing=delete_nodes,
        is_docker=is_docker,
        dlq_url=DLQ_URL,
        key_id=config_params_obj.aws_access_key,
        secret_key=config_params_obj.aws_secret_access_key,
        aws_region=config_params_obj.aws_region,
    )
    thread.start()

    return


if __name__ == "__main__":
    main()
