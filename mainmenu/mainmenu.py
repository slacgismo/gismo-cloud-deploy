from genericpath import exists
import imp
from importlib.resources import path
import coloredlogs, logging

from .classes.constants.EC2Actions import EC2Actions
from .classes.HandleEC2 import HandleEC2, create_ec2_object_from_existing_yaml
from .classes.constants.MenuActions import MenuActions
from .classes.Menu import Menu
from .classes.HandleAWS import HandleAWS
from .classes.constants.AWSActions import AWSActions
from .classes.constants.EKSActions import EKSActions
from os.path import exists
def mainmenu(
    saved_config_path_base:str = None,
    ec2_config_templates:str = None,
    eks_config_templates:str = None,
    aws_access_key:str = None,
    aws_secret_access_key:str  = None,
    aws_region:str = None,
    local_pem_path: str = None,
):
    logging.info("Main menu")

    # check if file exist
    if not exists(saved_config_path_base):
        logging.error(f"{saved_config_path_base} does not exist")
        return 
    if not exists(ec2_config_templates):
        logging.error(f"{ec2_config_templates} does not exist")
        return 
    if not exists(ec2_config_templates):
        logging.error(f"{ec2_config_templates} does not exist")
        return

    menus = Menu(
        saved_config_path_base= saved_config_path_base,
        ec2_config_templates= ec2_config_templates,
        eks_config_templates=  eks_config_templates,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region= aws_region,
        local_pem_path = local_pem_path
    )
    # start initialization state
    menus.select_main_menus()
    menus.hanlde_initialization()
    # end of initialization state

    # start to create handle ec2 object and check connection
    action = menus.get_menus_action()
    handle_ec2_object = None
    keypair_name = menus.get_keypair_name()
    ec2_tags = menus.get_ec2_tags()
    project_name = menus.get_project_name()
    saved_eks_cluster_file = None
    temp_project_path = menus.get_temp_project_path()
    

    handle_aws_object = HandleAWS(
            securitygroup_name = 'SSH-ONLY',
            local_pem_path=local_pem_path,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region= aws_region,
            keypair_name = keypair_name,
            tags=ec2_tags,
        )

    if action == MenuActions.create_cloud_resources_and_start.name:
        logging.info("Create all resources")
        # get default vpc id 
        vpc_id = handle_aws_object.get_default_vpc_id()
        # create security id 
        handle_aws_object.handle_aws_actions(action=AWSActions.create_securitygroup.name)
        security_group_ids = handle_aws_object.get_security_group_ids()
        # create keypair
        handle_aws_object.handle_aws_actions(action=AWSActions.create_keypair.name)
        pem_file_path = menus.get_local_pem_path()
        # create ec2 object from template
        handle_ec2_object = create_ec2_object_from_existing_yaml(
            saved_ec2_config_file=ec2_config_templates,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            pem_file_path = pem_file_path
        )
        # set security group
        handle_ec2_object.set_securitygroup_ids(securitygroup_ids=security_group_ids)
        handle_ec2_object.handle_ec2_action(action=EC2Actions.create.name)
        

    elif action == MenuActions.resume_from_existing.name or \
        action == MenuActions.cleanup_cloud_resources:
        logging.info("Wake up Ec2")

        saved_ec2_config_file = menus.get_saved_ec2_config_file()

        pem_file_path = menus.get_local_pem_path()
        handle_ec2_object = create_ec2_object_from_existing_yaml(
            saved_ec2_config_file=saved_ec2_config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            pem_file_path = pem_file_path
        )
        # wake up ec2
        handle_ec2_object.wakeup_ec2(wait_time=90, delay=1)

    
    logging.info("End of creation or wakeup ec2 state")
    # ec2 connection success
    # perfrom ec2 action state
    if action == MenuActions.create_cloud_resources_and_start.name \
        or action == MenuActions.resume_from_existing.name:
        logging.info("Update project folder")
        handle_ec2_object.ssh_upload_folder(
            local_project_path=temp_project_path,
            relative_project_folder_name=project_name
        )


        logging.info("Run command ssh")
        is_run_custom_ssh_command = menus.get_is_run_custom_ssh_command()
        if is_run_custom_ssh_command is True:
            handle_ec2_object.run_ssh_debug_mode()
        else:
            run_files_command = menus.get_run_files_command()
            handle_ec2_object.run_ssh_command(ssh_command=run_files_command)
    
        is_clean_up_after_completion = menus.get_cleanup_after_completion()
        if is_clean_up_after_completion is False:
            handle_ec2_object.handle_ec2_action(action=EC2Actions.stop.name)
        else:
            action == MenuActions.cleanup_cloud_resources.name

    elif action == MenuActions.run_in_local_machine.name:
        logging.info("Clean up resources")
    
    
    if saved_eks_cluster_file is None:
        logging.error("Something is wrong")
        return 

    if action == MenuActions.cleanup_cloud_resources.name:
        logging.info("Clean all resources")
        # delete cloud resources
        try:
            logging.info("Delete eks")
            handle_ec2_object.handle_ssh_eks_action(
                eks_action=EKSActions.delete.name,
                cluster_file =saved_eks_cluster_file,
                relative_saved_config_folder_name=project_name
            )

            logging.info("Terminate ec2")
            handle_ec2_object.handle_ec2_action(action=EC2Actions.terminate.name)
            handle_aws_object.set_aws_action(action=AWSActions.delete_keypair.name)
            menus.delete_saved_config_folder()
            # if all resources deletd . delte saved comfig folder
            menus.delete_saved_config_folder()
        except Exception as e:
            raise e

    logging.info("Clean local temp projects")
    menus.delete_project_folder()


    logging.info("===================")
    logging.info("End of Applications")
    logging.info("===================")
    