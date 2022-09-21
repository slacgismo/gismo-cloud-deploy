from email.policy import default
from multiprocessing.connection import wait
from multiprocessing.dummy import Process
from time import time
from modules.utils.SSHAction import SSHAction
from modules.utils.AWSActions import AWSActions
from modules.utils.EC2Status import EC2Status
from modules.utils.HandleEC2 import HandleEC2, create_ec2_object_from_dict
from modules.utils.EKSAction import EKSAction
from modules.utils.Menus import Menus
import click
import logging
import os
from pathlib import Path

from modules.utils.EC2Action import EC2Action
from modules.utils.HandleEC2Bastion import HandleEC2Bastion
from modules.utils.MenuAction import MenuAction
from modules.utils.run_process_files import run_process_files
from modules.utils.HandleAWS import HandleAWS
from dotenv import load_dotenv
import time
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
#  Meuns
# ***************************
@main.command()

def menus():
    base_path = os.getcwd()
    menus = Menus(
        saved_config_path_base= base_path+ "/projects/history",
        ec2_config_templates= base_path + "/config/ec2/config-ec2.yaml",
        eks_config_templates=  base_path + "/config/eks/cluster.yaml",
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_region= AWS_DEFAULT_REGION,
        local_pem_path = str(Path.home()) +"/.ssh"
    )
    menus.select_main_menus()
    # Initialization 
    menus.handle_prepare_actions()
    is_confirm = menus.get_confirmation_to_proness()
    
    if is_confirm is False:
        return
    menus_action = menus.get_menus_action()
    
    
   


    
    if menus_action == MenuAction.create_cloud_resources_and_start.name:
        logging.info("Create resources")
        
           # get ec2 
        project_in_tags = menus.get_project_in_tags()
        keypair_name = menus.get_keypair_name()
        local_pem_path = menus.get_local_pem_path()
        ec2_export_full_path_name = menus.get_ec2_export_full_path_name()
        eks_export_full_path_name = menus.get_eks_export_full_path_name()
        ec2_image_id = menus.get_ec2_image_id()
        ec2_instance_type = menus.get_ec2_instance_type()
        ec2_login_user = menus.get_ec2_login_user()
        ec2_volume = menus.get_ec2_volume()
        ec2_tags = menus.get_ec2_tags()
        local_project_path = menus.get_project_path()
        cluster_file = menus.get_cluster_file()
        relative_project_folder = menus.get_relative_project_folder()
        ssh_run_file_command = menus.get_run_files_command()
        is_cleanup_after_completion  = menus.get_cleanup_after_completion()
        print(f"is_confirm :{is_confirm}, menus_action {menus_action} project_in_tags: {project_in_tags}\n local_pem_path: {local_pem_path}\n ec2_export_full_path_name:{ec2_export_full_path_name}, \n eks_export_full_path_name: {eks_export_full_path_name},\n relative_project_folder:{relative_project_folder} \n ssh_command:{ssh_run_file_command}")
        print("----------------")
        
        handle_aws = HandleAWS(
            securitygroup_name = 'SSH-ONLY',
            local_pem_path=local_pem_path,
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region= AWS_DEFAULT_REGION,
            keypair_name = keypair_name,
            tags=ec2_tags,
        )
        # get default vpc id 
        vpc_id = handle_aws.get_default_vpc_id()
        # create security id 
        handle_aws.set_aws_action(action=AWSActions.create_securitygroup.name)
        handle_aws.handle_aws_actions()
        security_group_ids = handle_aws.get_security_group_ids()
        # create keypair
        handle_aws.set_aws_action(action=AWSActions.create_keypair.name)
        handle_aws.handle_aws_actions()
        # get ec2 export file 
        

        logging.info("Create Ec2")
        handle_ec2 = HandleEC2(
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region= AWS_DEFAULT_REGION,
            securitygroup_ids=security_group_ids,
            key_pair_name=keypair_name,
            vpc_id = vpc_id,
            export_full_path_name = ec2_export_full_path_name,
            ec2_image_id = ec2_image_id,
            ec2_instance_id = None,
            ec2_instance_type = ec2_instance_type,
            ec2_volume = ec2_volume, 
            pem_file_path = local_pem_path,
            login_user = ec2_login_user,
            tags = ec2_tags,
        )
        # pem_file_path = menus.get_pem_full_path_name()
        # pem2 = handle_ec2.get_pem_file_full_path_name()
        # print(pem_file_path, pem2)

        handle_ec2.set_ec2_action(action=EC2Action.create.name)
        handle_ec2.handle_ec2_action()
        handle_ec2.export_parameters_to_file()
        logging.info("SSH Installation")

        handle_ec2.ec2_ssh_installation(local_project_path=local_project_path)


        logging.info("Update cluster file")
        
        saved_eks_cluster_file = menus.get_saved_eks_config_file()
        relative_saved_config_files_folder_name = menus.get_relative_saved_config_files_folder_name()
        print(f"saved_eks_cluster_file :{saved_eks_cluster_file} relative_saved_config_files_folder_name:{relative_saved_config_files_folder_name}")
        handle_ec2.ssh_update_eks_cluster_file(
            local_cluster=saved_eks_cluster_file,
            saved_config_folder_name=relative_saved_config_files_folder_name
        )
        handle_ec2.ssh_update_eks_cluster_file_to_project_folder(
            local_cluster=saved_eks_cluster_file,
            project_folder_anme= relative_project_folder

        )

        logging.info("Create KES")

        handle_ec2.handle_ssh_eks_action(
            eks_action=EKSAction.create.name,
            cluster_file=cluster_file,
            relative_saved_config_folder_name=relative_saved_config_files_folder_name
        )


        is_run_custom_ssh_command = menus.get_is_run_custom_ssh_command()
        if is_run_custom_ssh_command is True:
            logging.info("run process file")
            is_breaking = False
            while not is_breaking:
                custom_ssh_command = handle_ec2.handle_input_ssh_custom_command()
                handle_ec2.run_ssh_command(
                    ssh_command=custom_ssh_command
                )
                logging.info("SSH command completed")
                is_breaking = handle_ec2.input_is_breaking_ssh()
            logging.info("Break ssh")

        else:
            handle_ec2.run_ssh_command(
                ssh_command=ssh_run_file_command
            )

        # always scale down nodes to zero of eks cluster 
        handle_ec2.handle_ssh_eks_action(
            eks_action=EKSAction.scaledownzero.name, 
            cluster_file=cluster_file,
            relative_project_folder_name=relative_project_folder
            )

        # Clean up
        if is_cleanup_after_completion is False:
           handle_ec2.set_ec2_action(action=EC2Action.stop.name)
           handle_ec2.handle_ec2_action()
        else:
            handle_ec2.handle_ssh_eks_action(eks_action=EKSAction.delete.name, cluster_file=cluster_file)
            handle_ec2.set_ec2_action(action=EC2Action.stop.name)
            handle_ec2.handle_ec2_action()
            handle_ec2.set_ec2_action(action=EC2Action.terminate.name)
            handle_ec2.handle_ec2_action()
            
        logging.info("=======================")
        logging.info("Application completed")
        logging.info("=======================")
       
    elif menus_action == MenuAction.resume_from_existing.name:

        logging.info("Resume from existing")
        saved_ec2_config_file = menus.get_saved_ec2_config_file()
       
        pem_file_path = menus.get_local_pem_path()
        saved_eks_cluster_file = menus.get_saved_eks_config_file()
        relative_project_folder = menus.get_relative_project_folder()
        relative_saved_config_files_folder_name = menus.get_relative_saved_config_files_folder_name()

       
        

        
        
        print(f"saved_eks_cluster_file : {saved_eks_cluster_file}")
        # pem_file = menus.get_pem_full_path_name()
        local_project_path = menus.get_project_path()
        handle_ec2 = create_ec2_object_from_dict(
            saved_ec2_config_file=saved_ec2_config_file,
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            pem_file_path = pem_file_path
        )

       

        
        # check ec2 status 
        waittime = 60
        delay = 1
        is_ec2_state_ready = False
        while waittime > 0 or not is_ec2_state_ready:
                waittime -= delay
                ec2_state =  handle_ec2.get_ec2_status()
                logging.info(f"ec2_state :{ec2_state} waitng:{waittime}")
                if ec2_state == EC2Status.stopped.name or ec2_state == EC2Status.running.name:
                    logging.info(f"In stopped or running {ec2_state}")
                    is_ec2_state_ready = True
                    break
                time.sleep(delay)
        if is_ec2_state_ready is False:
            logging.info("Wait ec2 state ready over time")
            return 
                

         # check ec2 status 
        if ec2_state == EC2Status.stopped.name:
            logging.info("EC2 in stop state, wake up ec2")
            handle_ec2.set_ec2_action(action=EC2Action.start.name)
            handle_ec2.handle_ec2_action()
        
        if ec2_state == EC2Status.running.name:
            logging.info("EC2 in running state")
            pass
            
        logging.info(f"Update project folder: {relative_project_folder}")
        handle_ec2.ssh_upload_folder(
            local_project_path=local_project_path,
            relative_project_folder_name=relative_project_folder
        )
        
        logging.info(f"Update eks file: {relative_project_folder}")
        handle_ec2.ssh_update_eks_cluster_file_to_project_folder(
            local_cluster=saved_eks_cluster_file,
            project_folder_anme= relative_project_folder

        )

        # Run any command 
        is_breaking = False
        while not is_breaking:
            custom_ssh_command = handle_ec2.handle_input_ssh_custom_command()
            handle_ec2.run_ssh_command(
                ssh_command=custom_ssh_command
            )
            logging.info("SSH command completed")
            is_breaking = handle_ec2.input_is_breaking_ssh()
        logging.info("Break ssh")

        is_clean_up = handle_ec2.hande_input_is_cleanup()
        if is_clean_up is True:
            logging.info("Clean up resources")
        else:
            logging.info("Stop ec2")
            handle_ec2.set_ec2_action(action=EC2Action.stop.name)
            handle_ec2.handle_ec2_action()
        
        logging.info("delete project folder")
        menus.delete_project_folder()
    
    elif menus_action == MenuAction.cleanup_cloud_resources.name:
        logging.info("Clean from existing")
        saved_ec2_config_file = menus.get_saved_ec2_config_file()
       
        pem_file_path = menus.get_local_pem_path()
        saved_eks_cluster_file = menus.get_saved_eks_config_file()
        relative_project_folder_name = menus.get_relative_project_folder()
        relative_saved_config_files_folder_name = menus.get_relative_saved_config_files_folder_name()
        keypair_name = menus.get_keypair_name()
        ec2_tags = menus.get_ec2_tags()
        print(f"saved_eks_cluster_file : {saved_eks_cluster_file}")
        # pem_file = menus.get_pem_full_path_name()
        local_project_path = menus.get_project_path()
        handle_ec2 = create_ec2_object_from_dict(
            saved_ec2_config_file=saved_ec2_config_file,
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            pem_file_path = pem_file_path
        )
        logging.info("Delete eks")
        handle_ec2.handle_ssh_eks_action(
            eks_action=EKSAction.delete.name,
            cluster_file =saved_eks_cluster_file,
            relative_saved_config_folder_name=relative_saved_config_files_folder_name
        )
        logging.info("Terminate ec2")
        handle_ec2.set_ec2_action(action=EC2Action.terminate.name)
        handle_ec2.handle_ec2_action()

        # keypair_name = handle_ec2.get
        handle_aws = HandleAWS(
            securitygroup_name = 'SSH-ONLY',
            local_pem_path=pem_file_path,
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region= AWS_DEFAULT_REGION,
            keypair_name = keypair_name,
            tags=ec2_tags,
        )
        # logging.info("Delete security group")
        # handle_aws.set_aws_action(action=AWSActions.delete_securitygroup.name)
        # handle_aws.handle_aws_actions()
            
        logging.info("Delete keypair")
        handle_aws.set_aws_action(action=AWSActions.delete_keypair.name)
        handle_aws.handle_aws_actions()
        logging.info("Delte saved config folder")
        menus.delete_saved_config_folder()
        logging.info("Delte project folder")
        menus.delete_project_folder()


    elif menus_action == MenuAction.run_in_local_machine.name:
        logging.info("Run in local machine")
        logging.info("Please read  `run-files --help` to process run-files command in your local machine!!")


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
    # handle_ec2_bastion.testing_fun()
    # return
    handle_ec2_bastion.set_ec2_action()
    # get action put
    action = handle_ec2_bastion.get_ec2_action()
    handle_ec2_bastion.handle_import_configfile()
    handle_ec2_bastion.change_config_parameters_from_input()
    handle_ec2_bastion.prepare_ec2()

    if action == EC2Action.start.name:
        is_confirm = handle_ec2_bastion.is_confirm_creation()
        if not is_confirm:
            return 
        handle_ec2_bastion.hanlde_create_cloud_resources()
        handle_ec2_bastion.handle_create_ec2()  
        handle_ec2_bastion.handle_install_dependencies()  
        # create eks
        handle_ec2_bastion.set_eks_action(action=EKSAction.create.name)
        handle_ec2_bastion.handle_eks_action()
        # run ssh command process file
        # handle_ec2_bastion.set_and_run_ssh_command()

    elif action == EC2Action.activate_from_existing.name:
        handle_ec2_bastion.handle_ssh_coonection()
        handle_ec2_bastion.handle_ssh_update()
        # handle_ec2_bastion.set_and_run_ssh_command()
        handle_ec2_bastion.set_eks_action(action=EKSAction.runfiles.name)
        handle_ec2_bastion.handle_eks_action()
        # check eks cluster if not exist, create a new cluster
        # run ssh command process file

    
    elif action == EC2Action.ssh.name:
        handle_ec2_bastion.handle_ssh_coonection()
        # run ssh command process file
        
    return
    # if clean up , clean up resource
    handle_ec2_bastion.handle_cleanup()

    
    logging.info("EC2 is ready, verify eks cluster")



    return 
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



'''
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-east-2 \
  --name my-mng \
  --node-type t2.large \
  --nodes 0 \
  --nodes-min 2 \
  --nodes-max 4 
#   --tags project=pvinisght 

'''    
