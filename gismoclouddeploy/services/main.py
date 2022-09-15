from email.policy import default
from multiprocessing.dummy import Process


import click
import logging
import os

from modules.utils.EC2Action import EC2Action
from modules.utils.HandleEC2Bastion import HandleEC2Bastion

from modules.utils.run_process_files import run_process_files

from dotenv import load_dotenv

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
    "--project",
    "-p",
    help="Project folder name",
    default="solardatatools",
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


def run_files(
    number: int = 1,
    scalenodes:int = 1,
    project: str = "solardatatools",
    repeat: int = 1

):
    """
    Proccess files in defined bucket
    :param number:      number of first n files in bucket. Default value is `None`.
                        If number is None, this application process defined files in config.yaml.
                        If number is 0, this application processs all files in the defined bucket in config.yaml.
                        If number is an integer, this applicaion process the first `number` files in the defined bucket in config.yaml.

    :param configfile:  Define config file name. Default value is "./config/config.yaml"

    """
    run_process_files(
        number=number,
        project = project,
        scale_nodes= scalenodes,
        repeat = repeat,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        ecr_repo=ECR_REPO,
    )


# ***************************
#  Handle EC2 Bastion
# ***************************
@main.command()

def handle_ec2():
    handle_ec2_bastion = HandleEC2Bastion(
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region= AWS_DEFAULT_REGION
    )


    handle_ec2_bastion.set_ec2_action()
    # get action put
    action = handle_ec2_bastion.get_ec2_action()

    handle_ec2_bastion.handle_import_configfile()
    if action == EC2Action.create_new.name:
        logging.info("Create a new project !!!")
    elif action == EC2Action.start_from_existing.name:
        logging.info("Start from existing project !!!")
    elif action == EC2Action.ssh.name:
        logging.info("Estibalish ssh connection from config file !!!")
    elif action == EC2Action.cleanup_resources.name:
         logging.info("Estibalish ssh connection from config file !!!")
    else:
        logging.error("Unknow action")

    return 
    if action == EC2Action.create.name:
        logger.info("Create instance and start from scratch !!!")
        handle_ec2_bastion.set_vpc_info()
        handle_ec2_bastion.set_security_group_info()
        handle_ec2_bastion.set_keypair_info()
        handle_ec2_bastion.set_ec2_info()
        handle_ec2_bastion.trigger_initial() 
        logging.info(f" ===== State: {handle_ec2_bastion.state} =======")
    
        is_confirm = handle_ec2_bastion.is_confirm_creation()
        if not is_confirm:
            return 
        logging.info(f" ===== State: {handle_ec2_bastion.state} =======")
        handle_ec2_bastion.trigger_resources_ready()
        logging.info(f" ===== State: {handle_ec2_bastion.state} =======")
        handle_ec2_bastion.trigger_create_ec2()
        logging.info(f" ===== State: {handle_ec2_bastion.state} =======")
        return 
        
    elif action == EC2Action.running.name or action == EC2Action.stop.name or action == EC2Action.terminate.name:
        logging.info("Import ec2 parameters and connect to ec2 throug ssh!!")
        handle_ec2_bastion.handle_import_configfile()
        handle_ec2_bastion.handle_ec2_action()
        return 
    elif action == EC2Action.ssh.name or action == EC2Action.ssh_create_eks.name or action == EC2Action.ssh_delete_eks.name:
        logging.info("Import ec2 parameters and connect to ec2 throug ssh!!")
        handle_ec2_bastion.handle_import_configfile()
        handle_ec2_bastion.trigger_ssh()
        handle_ec2_bastion.ssh_update_config_folder()
        is_breaking_ssh = handle_ec2_bastion.get_breaking_ssh()
        print(f"is_breaking_ssh :{is_breaking_ssh}" )
        if action == EC2Action.ssh.name:
            while not is_breaking_ssh:
                handle_ec2_bastion.set_and_run_ssh_command()
                handle_ec2_bastion.set_breaking_ssh()
            
                is_breaking_ssh = handle_ec2_bastion.get_breaking_ssh()
                logging.info(f"is_breaking_ssh: {is_breaking_ssh}")
            # step 5 , ssh upload files
        elif action == EC2Action.ssh_create_eks.name or action == EC2Action.ssh_delete_eks.name:
            handle_ec2_bastion.handle_eks_action()

        handle_ec2_bastion.set_ec2_action()
        handle_ec2_bastion.handle_ec2_action()

        # step 6 , set action stop or terminate

# ***************************
#  Main
# ***************************

if __name__ == "__main__":
    main()



    