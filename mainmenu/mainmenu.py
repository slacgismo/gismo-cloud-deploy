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
    is_confirm_to_process = menus.get_confirmation_to_proness()
    if is_confirm_to_process is False:
        logging.info("Application completion")
        return

    # start to create handle ec2 object and check connection
    action = menus.get_menus_action()
    keypair_name = menus.get_keypair_name()

    project_name = menus.get_project_name()
    temp_project_path = menus.get_temp_project_path()
    ec2_tags = menus.get_ec2_tags()
    print(f"keypair_name: {keypair_name}")

    handle_aws_object = HandleAWS(
            keypair_name = keypair_name,
            local_pem_path=local_pem_path,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region= aws_region,
            saved_config_path_base = saved_config_path_base,
            ec2_tags = ec2_tags,
            local_temp_project_path = temp_project_path,
            project_name = project_name
        )

    logging.info("Start prepare ec2 state")


    if action == MenuActions.create_cloud_resources_and_start.name:
        logging.info("Create resources")

        template_ec2_config_file = menus.get_ec2_template_file()
        template_eks_config_file = menus.get_eks_template_file()
        handle_aws_object.create_ec2_from_template_file(
            import_file=template_ec2_config_file
        )
        # generate eks cluster from template
        handle_aws_object.generate_eks_config_and_export(import_file = template_eks_config_file)
        # uplod cluster file to ec2
        handle_aws_object.ssh_update_eks_cluster_file()
        # create eks cluster
        handle_aws_object.handle_ssh_eks_action(eks_action=EKSActions.create.name)

        
    elif action == MenuActions.resume_from_existing.name or \
        action == MenuActions.cleanup_cloud_resources.name:
        saved_ec2_config_file = menus.get_saved_ec2_config_file()
        print(f"saved_ec2_config_file : {saved_ec2_config_file}")
        handle_aws_object.import_from_existing_ec2_config(config_file=saved_ec2_config_file)
        handle_aws_object.wake_up_ec2()

    logging.info("===============================")
    logging.info("End prepare ec2 state")
    logging.info("===============================")

    logging.info("Start perform command state")

    if action == MenuActions.create_cloud_resources_and_start.name or \
        action == MenuActions.resume_from_existing.name:
        logging.info("Update local temp project to ec2")
        handle_aws_object.ssh_upload_folder(
            local_project_path=temp_project_path,
            project_name=project_name
        )
        return 
        logging.info("Run command ssh")
        is_run_custom_ssh_command = menus.get_is_run_custom_ssh_command()
        if is_run_custom_ssh_command is True:
            handle_aws_object.run_ssh_debug_mode()
        else:
            run_files_command = menus.get_run_files_command()
            handle_aws_object.run_ssh_command(ssh_command=run_files_command)
    
        is_clean_up_after_completion = menus.get_cleanup_after_completion()

        # end of peform command , set action for next state
        if is_clean_up_after_completion is False:
            action = MenuActions.stop_ec2.name
        else:
            action == MenuActions.cleanup_cloud_resources.name

    elif action == MenuActions.run_in_local_machine.name:
        logging.info("Run files command in local machine")

    logging.info("===============================")
    logging.info("End perform command state")
    logging.info("===============================")

    return 
    logging.info("Start end state")
    if action == MenuActions.stop_ec2.name:
        handle_aws_object.handle_ec2_action(action=EC2Actions.stop.name)

    elif action == MenuActions.cleanup_cloud_resources.name:
        logging.info("clearn up action")
        try:
            saved_eks_cluster_file = menus.get_cluster_file()
            if saved_eks_cluster_file is None:
                logging.error("saved_eks_cluster_file is None")
                return 
            print(f"saved_eks_cluster_file, {saved_eks_cluster_file}, project_name :{project_name}")

            handle_aws_object.handle_ssh_eks_action(
                eks_action=EKSActions.delete.name,
                cluster_file =saved_eks_cluster_file,
                relative_saved_config_folder_name=project_name
            )

            logging.info("Terminate ec2")
            handle_aws_object.handle_ec2_action(action=EC2Actions.terminate.name)
            handle_aws_object.handle_ec2_action(action=AWSActions.delete_keypair.name)
            menus.delete_saved_config_folder()
            # if all resources deletd . delte saved comfig folder
        except Exception as e:
            raise e
            
    menus.delete_temp_project_folder()
    logging.info("===============================")
    logging.info("Application Completion")
    logging.info("===============================")


    # if action == MenuActions.create_cloud_resources_and_start.name:
    #     logging.info("Create all resources")
    #     # get default vpc id 
    #     vpc_id = handle_aws_object.get_default_vpc_id()
    #     # create security id 
    #     handle_aws_object.handle_aws_actions(action=AWSActions.create_securitygroup.name)
    #     security_group_ids = handle_aws_object.get_security_group_ids()
    #     # create keypair
    #     handle_aws_object.handle_aws_actions(action=AWSActions.create_keypair.name)
    #     pem_file_path = menus.get_local_pem_path()
        # create ec2 object from template
        # handle_ec2_object = create_ec2_object_from_existing_yaml(
        #     saved_ec2_config_file=ec2_config_templates,
        #     aws_access_key=aws_access_key,
        #     aws_secret_access_key=aws_secret_access_key,
        #     aws_region=aws_region,
        #     pem_file_path = pem_file_path
        # )
        # # set security group
        # handle_ec2_object.set_securitygroup_ids(securitygroup_ids=security_group_ids)
        # handle_ec2_object.handle_ec2_action(action=EC2Actions.create.name)
        

    # elif action == MenuActions.resume_from_existing.name or \
    #     action == MenuActions.cleanup_cloud_resources:
    #     logging.info("Wake up Ec2")
    #     handle_aws_object.wake_up_ec2(
            
    #     )
        # saved_ec2_config_file = menus.get_saved_ec2_config_file()
        # print(f"saved_ec2_config_file :{saved_ec2_config_file}")

        # pem_file_path = menus.get_local_pem_path()
        # handle_ec2_object = create_ec2_object_from_existing_yaml(
        #     saved_ec2_config_file=saved_ec2_config_file,
        #     aws_access_key=aws_access_key,
        #     aws_secret_access_key=aws_secret_access_key,
        #     aws_region=aws_region,
        #     pem_file_path = pem_file_path
        # )
        # # wake up ec2
        # handle_ec2_object.wakeup_ec2(wait_time=90, delay=1)

    
    # logging.info("End of creation or wakeup ec2 state")
    # # ec2 connection success
    # # perfrom ec2 action state
    # if action == MenuActions.create_cloud_resources_and_start.name \
    #     or action == MenuActions.resume_from_existing.name:
        # logging.info("Update project folder")
        # handle_ec2_object.ssh_upload_folder(
        #     local_project_path=temp_project_path,
        #     relative_project_folder_name=project_name
        # )


        # logging.info("Run command ssh")
        # is_run_custom_ssh_command = menus.get_is_run_custom_ssh_command()
        # if is_run_custom_ssh_command is True:
        #     handle_ec2_object.run_ssh_debug_mode()
        # else:
        #     run_files_command = menus.get_run_files_command()
        #     handle_ec2_object.run_ssh_command(ssh_command=run_files_command)
    
        # is_clean_up_after_completion = menus.get_cleanup_after_completion()
        # if is_clean_up_after_completion is False:
        #     handle_ec2_object.handle_ec2_action(action=EC2Actions.stop.name)
        # else:
        #     action == MenuActions.cleanup_cloud_resources.name

    # elif action == MenuActions.run_in_local_machine.name:
    #     logging.info("Clean up resources")
    
    


    # if action == MenuActions.cleanup_cloud_resources.name:
    #     logging.info("Clean all resources")
    #     # delete cloud resources
        # try:
        #     logging.info("Delete eks")
        #     saved_eks_cluster_file = menus.get_cluster_file()
        #     if saved_eks_cluster_file is None:
        #         logging.error("saved_eks_cluster_file is None")
        #         return 
        #     if handle_ec2_object is None:
        #         logging.error("handle_ec2_object is None")
        #         return 
        #     print(f"saved_eks_cluster_file, {saved_eks_cluster_file}, project_name :{project_name}")

        #     handle_ec2_object.handle_ssh_eks_action(
        #         eks_action=EKSActions.delete.name,
        #         cluster_file =saved_eks_cluster_file,
        #         relative_saved_config_folder_name=project_name
        #     )

        #     logging.info("Terminate ec2")
        #     handle_ec2_object.handle_ec2_action(action=EC2Actions.terminate.name)
        #     handle_aws_object.set_aws_action(action=AWSActions.delete_keypair.name)
        #     menus.delete_saved_config_folder()
        #     # if all resources deletd . delte saved comfig folder
        #     menus.delete_saved_config_folder()
        # except Exception as e:
        #     raise e

    # logging.info("Clean local temp projects")
    # menus.delete_project_folder()


    logging.info("===================")
    logging.info("End of Applications")
    logging.info("===================")
    