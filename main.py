
from mainmenu.classes.utilities.aws_utitlties import check_environment_is_aws
from mainmenu.mainmenu import mainmenu
import click
import logging
import os
from pathlib import Path
from gismoclouddeploy.utils.run_process_files import run_process_files
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
    default="examples/solardatatools",
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

    run_process_files(
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
    
    # menus = Menu(
        # saved_config_path_base= base_path+ "/projects/history",
        # ec2_config_templates= base_path + "/config/ec2/config-ec2.yaml",
        # eks_config_templates=  base_path + "/config/eks/cluster.yaml",
        # aws_access_key=AWS_ACCESS_KEY_ID,
        # aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        # aws_region= AWS_DEFAULT_REGION,
        # local_pem_path = str(Path.home()) +"/.ssh"
    # )
#     menus.select_main_menus()
#     # Initialization 
#     menus.handle_prepare_actions()
#     is_confirm = menus.get_confirmation_to_proness()
    
#     if is_confirm is False:
#         return
#     menus_action = menus.get_menus_action()
    
    
    
#     if menus_action == MenuAction.create_cloud_resources_and_start.name:
#         logging.info("Create resources")
        
#            # get ec2 
#         project_in_tags = menus.get_project_in_tags()
#         keypair_name = menus.get_keypair_name()
#         local_pem_path = menus.get_local_pem_path()
#         ec2_export_full_path_name = menus.get_ec2_export_full_path_name()
#         eks_export_full_path_name = menus.get_eks_export_full_path_name()
#         ec2_image_id = menus.get_ec2_image_id()
#         ec2_instance_type = menus.get_ec2_instance_type()
#         ec2_login_user = menus.get_ec2_login_user()
#         ec2_volume = menus.get_ec2_volume()
#         ec2_tags = menus.get_ec2_tags()
#         local_project_path = menus.get_project_path()
#         cluster_file = menus.get_cluster_file()
#         relative_project_folder = menus.get_relative_project_folder()
#         ssh_run_file_command = menus.get_run_files_command()
#         is_cleanup_after_completion  = menus.get_cleanup_after_completion()

        
#         handle_aws = HandleAWS(
#             securitygroup_name = 'SSH-ONLY',
#             local_pem_path=local_pem_path,
#             aws_access_key=AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#             aws_region= AWS_DEFAULT_REGION,
#             keypair_name = keypair_name,
#             tags=ec2_tags,
#         )
#         # get default vpc id 
#         vpc_id = handle_aws.get_default_vpc_id()
#         # create security id 
#         handle_aws.set_aws_action(action=AWSActions.create_securitygroup.name)
#         handle_aws.handle_aws_actions()
#         security_group_ids = handle_aws.get_security_group_ids()
#         # create keypair
#         handle_aws.set_aws_action(action=AWSActions.create_keypair.name)
#         handle_aws.handle_aws_actions()
#         # get ec2 export file 
        

#         logging.info("Create Ec2")
#         handle_ec2 = HandleEC2(
#             aws_access_key=AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#             aws_region= AWS_DEFAULT_REGION,
#             securitygroup_ids=security_group_ids,
#             key_pair_name=keypair_name,
#             vpc_id = vpc_id,
#             export_full_path_name = ec2_export_full_path_name,
#             ec2_image_id = ec2_image_id,
#             ec2_instance_id = None,
#             ec2_instance_type = ec2_instance_type,
#             ec2_volume = ec2_volume, 
#             pem_file_path = local_pem_path,
#             login_user = ec2_login_user,
#             tags = ec2_tags,
#         )
#         handle_ec2.set_ec2_action(action=EC2Action.create.name)
#         handle_ec2.handle_ec2_action()
#         handle_ec2.export_parameters_to_file()
#         logging.info("SSH Installation")

#         handle_ec2.ec2_ssh_installation(local_project_path=local_project_path)


#         logging.info("Update cluster file")
        
#         saved_eks_cluster_file = menus.get_saved_eks_config_file()
#         relative_saved_config_files_folder_name = menus.get_relative_saved_config_files_folder_name()
#         print(f"saved_eks_cluster_file :{saved_eks_cluster_file} relative_saved_config_files_folder_name:{relative_saved_config_files_folder_name}")
#         handle_ec2.ssh_update_eks_cluster_file(
#             local_cluster=saved_eks_cluster_file,
#             saved_config_folder_name=relative_saved_config_files_folder_name
#         )
#         logging.info("Create KES")
#         handle_ec2.handle_ssh_eks_action(
#             eks_action=EKSAction.create.name,
#             cluster_file=cluster_file,
#             relative_saved_config_folder_name=relative_saved_config_files_folder_name
#         )
#         is_run_custom_ssh_command = menus.get_is_run_custom_ssh_command()
#         if is_run_custom_ssh_command is True:
#             logging.info("run process file")
#             is_breaking = False
#             while not is_breaking:
#                 custom_ssh_command = handle_ec2.handle_input_ssh_custom_command()
#                 handle_ec2.run_ssh_command(
#                     ssh_command=custom_ssh_command
#                 )
#                 logging.info("SSH command completed")
#                 is_breaking = handle_ec2.input_is_breaking_ssh()
#             logging.info("Break ssh")

#         else:
#             handle_ec2.run_ssh_command(
#                 ssh_command=ssh_run_file_command
#             )

#         # always scale down nodes to zero of eks cluster 
#         handle_ec2.handle_ssh_eks_action(
#             eks_action=EKSAction.scaledownzero.name, 
#             cluster_file=cluster_file,
#             relative_project_folder_name=relative_project_folder
#             )

#         # Clean up
#         if is_cleanup_after_completion is False:
#            handle_ec2.set_ec2_action(action=EC2Action.stop.name)
#            handle_ec2.handle_ec2_action()
#         else:
#             handle_ec2.handle_ssh_eks_action(eks_action=EKSAction.delete.name, cluster_file=cluster_file)
#             handle_ec2.set_ec2_action(action=EC2Action.stop.name)
#             handle_ec2.handle_ec2_action()
#             handle_ec2.set_ec2_action(action=EC2Action.terminate.name)
#             handle_ec2.handle_ec2_action()
            
#         logging.info("=======================")
#         logging.info("Application completed")
#         logging.info("=======================")
       
#     elif menus_action == MenuAction.resume_from_existing.name:

#         logging.info("Resume from existing ----------")
#         saved_ec2_config_file = menus.get_saved_ec2_config_file()
   
#         pem_file_path = menus.get_local_pem_path()
#         saved_eks_cluster_file = menus.get_saved_eks_config_file()
#         relative_project_folder = menus.get_relative_project_folder()
#         relative_saved_config_files_folder_name = menus.get_relative_saved_config_files_folder_name()
#         ssh_run_file_command = menus.get_run_files_command()
#         # pem_file = menus.get_pem_full_path_name()
#         local_project_path = menus.get_project_path()
#         handle_ec2 = create_ec2_object_from_dict(
#             saved_ec2_config_file=saved_ec2_config_file,
#             aws_access_key=AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#             aws_region=AWS_DEFAULT_REGION,
#             pem_file_path = pem_file_path
#         )

#         # check ec2 status 
#         waittime = 60
#         delay = 1
#         is_ec2_state_ready = False
#         while waittime > 0 or not is_ec2_state_ready:
#                 waittime -= delay
#                 ec2_state =  handle_ec2.get_ec2_status()
#                 logging.info(f"ec2_state :{ec2_state} waitng:{waittime}")
#                 if ec2_state == EC2Status.stopped.name or ec2_state == EC2Status.running.name:
#                     logging.info(f"In stopped or running {ec2_state}")
#                     is_ec2_state_ready = True
#                     break
#                 time.sleep(delay)
       

        
#         if is_ec2_state_ready is False:
#             logging.info("Wait ec2 state ready over time")
#             return 
                

#          # check ec2 status 
#         if ec2_state == EC2Status.stopped.name:
#             logging.info("EC2 in stop state, wake up ec2")
#             handle_ec2.set_ec2_action(action=EC2Action.start.name)
#             handle_ec2.handle_ec2_action()
        
#         if ec2_state == EC2Status.running.name:
#             logging.info("EC2 in running state")
#             pass
            
#         logging.info(f"Update project folder: {relative_project_folder}")
#         handle_ec2.ssh_upload_folder(
#             local_project_path=local_project_path,
#             relative_project_folder_name=relative_project_folder
#         )
        
#         is_run_custom_ssh_command = menus.get_is_run_custom_ssh_command()
#         if is_run_custom_ssh_command is True:
#             # Run any command 
#             is_breaking = False
#             while not is_breaking:
#                 custom_ssh_command = handle_ec2.handle_input_ssh_custom_command()
#                 handle_ec2.run_ssh_command(
#                     ssh_command=custom_ssh_command
#                 )
#                 logging.info("SSH command completed")
#                 is_breaking = handle_ec2.input_is_breaking_ssh()
#             logging.info("Break ssh")
           
#         else:
#             handle_ec2.run_ssh_command(
#                 ssh_command=ssh_run_file_command
#             )
        

#         is_clean_up = handle_ec2.hande_input_is_cleanup()
#         if is_clean_up is True:
#             logging.info("Clean up resources")
#         else:
#             logging.info("Stop ec2")
#             handle_ec2.set_ec2_action(action=EC2Action.stop.name)
#             handle_ec2.handle_ec2_action()
        
#         logging.info("delete project folder")
#         menus.delete_project_folder()
    
#     elif menus_action == MenuAction.cleanup_cloud_resources.name:
#         logging.info("Clean from existing")
#         saved_ec2_config_file = menus.get_saved_ec2_config_file()
       
#         pem_file_path = menus.get_local_pem_path()
#         saved_eks_cluster_file = menus.get_saved_eks_config_file()
#         relative_project_folder_name = menus.get_relative_project_folder()
#         relative_saved_config_files_folder_name = menus.get_relative_saved_config_files_folder_name()
#         keypair_name = menus.get_keypair_name()
#         ec2_tags = menus.get_ec2_tags()
#         print(f"saved_eks_cluster_file : {saved_eks_cluster_file}")
#         # pem_file = menus.get_pem_full_path_name()
#         local_project_path = menus.get_project_path()
#         handle_ec2 = create_ec2_object_from_dict(
#             saved_ec2_config_file=saved_ec2_config_file,
#             aws_access_key=AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#             aws_region=AWS_DEFAULT_REGION,
#             pem_file_path = pem_file_path
#         )
#         # check ec2 status 
#         waittime = 60
#         delay = 1
#         is_ec2_state_ready = False
#         while waittime > 0 or not is_ec2_state_ready:
#                 waittime -= delay
#                 ec2_state =  handle_ec2.get_ec2_status()
#                 logging.info(f"ec2_state :{ec2_state} waitng:{waittime}")
#                 if ec2_state == EC2Status.stopped.name or ec2_state == EC2Status.running.name:
#                     logging.info(f"In stopped or running {ec2_state}")
#                     is_ec2_state_ready = True
#                     break
#                 time.sleep(delay)

#         if is_ec2_state_ready is False:
#             logging.info("Wait ec2 state ready over time")
#             return 

#         logging.info("Delete eks")
#         handle_ec2.handle_ssh_eks_action(
#             eks_action=EKSAction.delete.name,
#             cluster_file =saved_eks_cluster_file,
#             relative_saved_config_folder_name=relative_saved_config_files_folder_name
#         )
#         logging.info("Terminate ec2")
#         handle_ec2.set_ec2_action(action=EC2Action.terminate.name)
#         handle_ec2.handle_ec2_action()

#         # keypair_name = handle_ec2.get
#         handle_aws = HandleAWS(
#             securitygroup_name = 'SSH-ONLY',
#             local_pem_path=pem_file_path,
#             aws_access_key=AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#             aws_region= AWS_DEFAULT_REGION,
#             keypair_name = keypair_name,
#             tags=ec2_tags,
#         )
#         # logging.info("Delete security group")
#         # handle_aws.set_aws_action(action=AWSActions.delete_securitygroup.name)
#         # handle_aws.handle_aws_actions()
            
#         logging.info("Delete keypair")
#         handle_aws.set_aws_action(action=AWSActions.delete_keypair.name)
#         handle_aws.handle_aws_actions()
#         logging.info("Delte saved config folder")
#         menus.delete_saved_config_folder()
#         logging.info("Delte project folder")
#         menus.delete_project_folder()


#     elif menus_action == MenuAction.run_in_local_machine.name:
#         logging.info("Run in local machine")
#         logging.info("Please read  `run-files --help` to process run-files command in your local machine!!")


# ***************************
#  Main
# ***************************

if __name__ == "__main__":
    main()


