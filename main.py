
from mainmenu.mainmenu import mainmenu
from mainmenu.classes.utilities.aws_utitlties import check_environment_is_aws

import click
import logging
import os
from pathlib import Path
from gismoclouddeploy.gismoclouddeploy import gismoclouddeploy
from dotenv import load_dotenv
load_dotenv()



AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")
# SQS_URL = os.getenv("SQS_URL")  # aws standard url
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
    "--project",
    "-p",
    help="Project folder name",
    default="examples/sleep",
)
@click.option(
    "--scalenodes",
    "-s",
    help="Total number of nodes(instances)",
    default=1,
)
@click.option(
    "--repeat",
    "-r",
    help="Repeat time",
    default=1,
)

@click.option(
    "--cluster",
    "-c",
    help="eks cluster name, if run in local, just use defaul 'local'",
    default="local",
)


@click.option(
    "--nodegroup_name",
    "-nd",
    help="eks cluster nodegroup name, default is 'gcd'. It's hardcode in config/eks/cluster.yaml ",
    default="gcd",
)


@click.option(
    "--instance_type",
    "-in",
    help="eks node instance type , default is 't2.large'. It's hardcode in config/eks/cluster.yaml ",
    default="t2.large",
)

@click.option(
    "--file",
    "-f",
    help="run specific file)",
    multiple=True
)


def run_files(
    number: int = 1,
    scalenodes:int = 1,
    project: str = "examples/solardatatools",
    repeat: int = 1,
    cluster: str = 'local',
    nodegroup_name: str = 'gcd',
    instance_type:str = 't2.large',
    file:str = None
):
    """
    Proccess files in defined bucket
    :param number:      number of first n files in bucket. Default value is `None`.
                        If number is None, this application process defined files in config.yaml.
                        If number is 0, this application processs all files in the defined bucket in config.yaml.
                        If number is an integer, this applicaion process the first `number` files in the defined bucket in config.yaml.

    :param configfile:  Define config file name. Default value is "./config/config.yaml"

    """
    if (len(file) < 1) and number is None:
        click.echo("No number input nor file input. Please enter number or file input")
        return  

    if (len(file) >= 1) and (number is not None):
        click.echo("Both file input and number input have been given. You can only choice one.")
        return 
    if cluster =="local" and check_environment_is_aws():
        click.echo("Runing application on AWS environment. Please use '-c' option command to specify a cluster name.")
        return 

    default_fileslist = []
    if len(file)>= 1:
        # convert input file tuple to a list
        files = list(file)
        default_fileslist = files

    gismoclouddeploy(
        number=number,
        project = project,
        scale_nodes= scalenodes,
        repeat = repeat,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        ecr_repo=ECR_REPO,
        cluster = cluster,
        nodegroup_name = nodegroup_name,
        instance_type= instance_type,
        default_fileslist = default_fileslist
    )


# ***************************
#  Meuns
# ***************************
@main.command()

def menu():
    base_path = os.getcwd()  
    home_dir = str(Path.home())  # ~/

    mainmenu(
        saved_config_path_base= base_path+ "/created_resources_history",
        ec2_config_templates= base_path + "/mainmenu/config/ec2/config-ec2.yaml",
        eks_config_templates=  base_path + "/mainmenu/config/eks/cluster.yaml",
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region= AWS_DEFAULT_REGION,
        local_pem_path = home_dir +"/.ssh"
    )

# ***************************
#  Main
# ***************************

if __name__ == "__main__":
    main()


