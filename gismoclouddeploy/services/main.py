from multiprocessing.dummy import Process

import click
import logging
import os

import modules
from modules.utils.AWS_CONFIG import AWS_CONFIG
from modules.utils.WORKER_CONFIG import WORKER_CONFIG
from modules.utils.run_process_files import run_process_files
from modules.utils.save_cached_and_plot import save_cached_and_plot
from modules.utils.modiy_config_parameters import modiy_config_parameters
from modules.utils.eks_utils import scale_eks_nodes_and_wait
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
    "--build",
    "-b",
    is_flag=True,
    help="Build a temp image and use it. If on AWS k8s environment, \
    build and push image to ECR with temp image tag. These images will be deleted after used.\
    If you would like to preserve images, please use build-image command instead ",
)
@click.option(
    "--nodesscale",
    "-sc",
    help="Scale up eks nodes and worker replcas as the same number. This input number replaces the worker_repliacs and eks_nodes_number in config files",
    default=None,
)
def run_files(
    number: int = 1,
    deletenodes: bool = False,
    configfile: str = None,
    rollout: str = False,
    imagetag: str = "latest",
    docker: bool = False,
    build: bool = False,
    nodesscale: int = None,
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
    :param imagetag:    Specifiy the image tag. Default value is 'latest'.This option command did not work with [ -b | --build ] option command.
    :param docker:      Default value is False. If it is True, the services run in docker environment.
                        Otherwise, the services run in k8s environment.
    :param build:       Build a temp image and use it. If on AWS k8s environment, \
                        build and push image to ECR with temp image tag. These images will be deleted after used.\
                        If you would like to preserve images, please use build-image command instead
    :param nodesscale:  Scale up eks nodes and worker replcas as the same number. \
                        This input number replaces the worker_repliacs and eks_nodes_number in config files
    """
    run_process_files(
        number=number,
        delete_nodes=deletenodes,
        configfile=configfile,
        rollout=rollout,
        image_tag=imagetag,
        is_docker=docker,
        is_build_image=build,
        nodesscale=nodesscale,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        sqs_url=SQS_URL,
        sns_topic=SNS_TOPIC,
        ecr_repo=ECR_REPO,
        dlq_url=DLQ_URL,
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
    config_json = modiy_config_parameters(
        configfile=configfile,
        nodesscale=None,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        sqs_url=SQS_URL,
        sns_topic=SNS_TOPIC,
        dlq_url=DLQ_URL,
        ecr_repo=ECR_REPO,
    )
    aws_config_obj = AWS_CONFIG(config_json["aws_config"])

    # worker_config_obj = WORKER_CONFIG(config_json["worker_config"])
    scale_eks_nodes_and_wait(
        scale_node_num=int(min_nodes),
        total_wait_time=aws_config_obj.scale_eks_nodes_wait_time,
        delay=1,
        cluster_name=aws_config_obj.cluster_name,
        nodegroup_name=aws_config_obj.nodegroup_name,
    )


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


@main.command()
@click.option(
    "--configfile",
    "-f",
    help="Assign custom config files, Default files name is ./config/config.yaml",
    default="config.yaml",
)
def save_cached(configfile):
    """
    Save cached data from previous process.
    """
    click.echo("save cached data from previous process")

    save_cached_and_plot(
        configfile=configfile,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        sqs_url=SQS_URL,
        sns_topic=SNS_TOPIC,
        ecr_repo=ECR_REPO,
        dlq_url=DLQ_URL,
    )


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


if __name__ == "__main__":
    main()
