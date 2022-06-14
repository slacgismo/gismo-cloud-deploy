from asyncio import threads
from concurrent.futures import thread
import re
import threading
from unicodedata import name
from urllib import response
import click
from os.path import exists
import logging
import os


import modules
from server.models.Configurations import make_config_obj_from_yaml
from server.utils.aws_utils import check_aws_validity, connect_aws_client

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
    help="Process the first n files in bucket, if number=0, run all files in the bucket",
    default=None,
)
@click.option(
    "--deletenodes",
    "-d",
    is_flag=True,
    help="Enbale or disable delet nodes after process, default is Ture. Set False to disable ",
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
@click.option(
    "--imagetag",
    "-i",
    help="Select images base on the branch. Default image branch is latest",
    default="latest",
)
def run_files(number, deletenodes, configfile, rollout, imagetag):
    """Run Process Files"""
    run_process_files(
        number=number,
        delete_nodes=deletenodes,
        configfile=configfile,
        rollout=rollout,
        images_tag=imagetag,
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
    logger.info(f"Scale nodes {min_nodes}")
    try:
        # config_obj = import_config_from_yaml(configfile)
        config_params_obj = make_config_obj_from_yaml(
            file=f"./config/{configfile}",
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
def build_and_push(tag):
    """Check nodes status"""
    click.echo(f"Build and push image:{tag}")
    res = modules.utils.invoke_docker_compose_build()
    click.echo(res)
    validation_res = modules.utils.invoke_ecr_validation()
    click.echo(validation_res)
    click.echo(f"tag {ECR_REPO}/worker:{tag}")
    tag_worker = modules.utils.invoke_tag_image(
        image_name="worker",
        image_tag=tag,
        ecr_repo="041414866712.dkr.ecr.us-east-2.amazonaws.com",
    )
    click.echo("tag_worker")
    click.echo(f"tag {ECR_REPO}/server:{tag}")
    tag_server = modules.utils.invoke_tag_image(
        image_name="server",
        image_tag=tag,
        ecr_repo="041414866712.dkr.ecr.us-east-2.amazonaws.com",
    )
    click.echo("tag_server")
    click.echo(f"tag {ECR_REPO}/worker:{tag}")
    push_worker = modules.utils.invoke_push_image(
        image_name="worker", image_tag=tag, ecr_repo=ECR_REPO
    )
    click.echo(push_worker)
    click.echo(f"tag {ECR_REPO}/server:{tag}")
    push_server = modules.utils.invoke_push_image(
        image_name="server", image_tag=tag, ecr_repo=ECR_REPO
    )
    click.echo(push_server)


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
def k8s_deploy(tag: str, local: bool, configfile: str):
    click.echo(f"check k8s image {tag}: environment is AWS:{local}")
    run_k8s_deploy(image_tag=tag, is_local_environem=local, configfile=configfile)
    # worker_image, worker_image_tag = modules.utils.eks_utils.get_k8s_image_and_tag_from_deployment(prefix="worker")
    # webapp_image, webapp_image_tag = modules.utils.eks_utils.get_k8s_image_and_tag_from_deployment(prefix="webapp")
    # print(worker_image,worker_image_tag,webapp_image,webapp_image_tag)

    # if worker_image_tag != tag or webapp_image_tag != tag:
    #     logger.info("========= Delete current deployment =============")
    #     response = invoke_kubectl_delete_deployment()
    #     logger.info(response)


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


def run_k8s_deploy(image_tag: str, is_local_environem: bool, configfile: str):
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
        from server.utils.aws_utils import check_ecr_tag_exists

        ecr_client = connect_aws_client(
            client_name="ecr",
            key_id=config_params_obj.aws_access_key,
            secret=config_params_obj.aws_secret_access_key,
            region=config_params_obj.aws_region,
        )

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
            name=service_name,
            image_tag=image_tag,
            imagePullPolicy=imagePullPolicy,
            desired_replicas=desired_replicas,
            k8s_file_name=deployment_file,
        )
        # service exists
        if service_file:
            # check service exist
            if not modules.utils.eks_utils.check_k8s_services_exists(name=service_name):
                logger.info(f"========= Create services{service_file} =========== ")
                modules.utils.eks_utils.create_k8s_svc_from_yaml(
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


import sys


class ExcThread(threading.Thread):
    def __init__(self, bucket):
        threading.Thread.__init__(self)
        self.bucket = bucket

    def run(self):
        try:
            raise Exception("An error occured here.")
        except Exception:
            self.bucket.put(sys.exc_info())

    # #2. chcek if k8s exist, check tag
    # 2.1 if tag is not correct, delete current deployment, apply new image
    # 3. if tag is correct. check replicas
    # 3.1. if replicas is not correct , attached new replicas
    # 4. wait pod ready with correct replicas


def run_process_files(number, delete_nodes, configfile, rollout, images_tag):
    """
    Proccess files in S3 bucket
    :param number: number of first n files in bucket
    :param delete_nodes: delete node after process files
    :param configfile: config file name
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

    try:
        modules.command_utils.check_environment_setup(
            config_params_obj=config_params_obj, rollout=rollout, images_tag=images_tag
        )
    except Exception as e:
        logger.error(f"Environemnt setup failed :{e}")
        return

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
            number=number, config_params_obj=config_params_obj, config_yaml=config_yaml
        )

    except Exception as e:
        logger.error(f"Invoke process files error:{e}")
        return

    thread = modules.TaskThread(
        threadID=1,
        name="sqs",
        counter=120,
        wait_time=2,
        sqs_url=SQS_URL,
        num_task=total_task_num,
        config_params_obj=config_params_obj,
        delete_nodes_after_processing=delete_nodes,
        dlq_url=DLQ_URL,
        key_id=config_params_obj.aws_access_key,
        secret_key=config_params_obj.aws_secret_access_key,
        aws_region=config_params_obj.aws_region,
    )
    thread.start()

    return


if __name__ == "__main__":
    main()
