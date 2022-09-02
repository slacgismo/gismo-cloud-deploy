from multiprocessing.dummy import Process

import click
import logging
import os

from modules.utils.AWS_CONFIG import AWS_CONFIG
from modules.utils.run_process_files import run_process_files
from modules.utils.create_eks_cluster import create_eks_cluster,delete_eks_cluster,handle_eks_cluster_action
from modules.utils.create_ec2 import create_ec2_keypair,handle_ec2_bastion
from modules.utils.modiy_config_parameters import modiy_config_parameters
from modules.utils.eks_utils import scale_eks_nodes_and_wait
from modules.utils.check_aws import check_environment_is_aws
from modules.utils.invoke_function import invoke_force_delete_namespace
from modules.utils.handle_run_files_ssh import handle_run_files_ssh
from dotenv import load_dotenv
from modules.utils.command_utils import print_dlq
from modules.utils.invoke_function import invoke_docker_compose_build,invoke_ecr_validation,invoke_tag_image
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")
# SQS_URL = os.getenv("SQS_URL")  # aws standard url
ECR_REPO = os.getenv("ECR_REPO")  # get ecr repo
PEM_LOCATION = os.getenv("PEM_LOCATION") 
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
@click.option(
    "--repeatnumber",
    "-rn",
    help="Scale up eks nodes and worker replcas as the same number. This input number replaces the worker_repliacs and eks_nodes_number in config files",
    default=1,
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
    repeatnumber :int = 1,
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
        ecr_repo=ECR_REPO,
        repeatnumber=repeatnumber,

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
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
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
#  Handle EKS cluster action, Create, Delete, List cluster
# ***************************
@main.command()
@click.option(
    "--configfile",
    "-f",
    help="Assign custom config files, Default files name is ./config/config.yaml",
    default="config.yaml",
)
@click.argument("action")
def handle_ekscluster(configfile, action):
    """Create cluster from config file"""
    click.echo(f"handle cluster from :{configfile} action:{action}")

    # step 1 , check environmnet if local . link to ec2 bastion
    handle_eks_cluster_action(
        config_file=configfile, 
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        action = action
        )



# ***************************
#  Handle run-files on AWS through ssh 
# ***************************
@main.command()
@click.option(
    "--configfile",
    "-f",
    help="Assign custom config files, Default files name is ./config/config.yaml",
    default="config.yaml",
)
@click.argument("command")
def ssh_runfiles(configfile, command):
    """Use local machine to handle run-files command on AWS through SSH """
    click.echo(f"handle cluster from :{configfile} action:{command}")

    handle_run_files_ssh(
        config_file=configfile, 
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        command = command
        )
        
    
# ***************************
#  Create Key Pair 
# ***************************
@main.command()
@click.argument("keyname")
@click.argument("file_location")

def create_keypair(keyname,file_location ):
    """Create EC2 from config file"""
    click.echo(f"Create keypair :{keyname} save to  :{file_location}")

    create_ec2_keypair(
        keyname = keyname,
        file_location = file_location,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION)



# ***************************
#  Handle EC2 Action, List,  Create , Start, Stop, or Terminate EC2 Instances
# ***************************
@main.command()
@click.option(
    "--configfile",
    "-f",
    help="Assign custom config files, Default files name is ./config/config.yaml",
    default="config.yaml",
)
@click.argument("action")

def handle_ec2(configfile, action):
    """Handle EC2 action"""
    
    handle_ec2_bastion(
        config_file=configfile, 
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        action = action
        )


# ***************************
#  Force delete namespace 
# ***************************
@main.command()
@click.argument("namespace")

def delete_namespace(namespace):
    """Force delete namesapce """
    click.echo(f"Force delete namespace :{namespace}")

    res = invoke_force_delete_namespace(namespace = namespace)

    click.echo(f"Response  :{res}")


# ***************************
#  Main
# ***************************

if __name__ == "__main__":
    main()



    