
from genericpath import exists

import sys
import os
# setting path


import logging
from tkinter import E

from mainmenu.classes.constants.Platform import Platform

from .classes.constants.EC2Actions import EC2Actions
from .classes.constants.MenuActions import MenuActions
from .classes.FiniteStateMachine import FiniteStateMachine
from .classes.AWSServices import AWSServices
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

    # check local_pem_path exist 
    if not exists(local_pem_path):
        try:
            os.mkdir(local_pem_path)
            logging.info(f"Create {local_pem_path} success")
        except Exception as e:
            raise Exception(f"Create {local_pem_path} failed")


    return 
    fsm = FiniteStateMachine(
        saved_config_path_base= saved_config_path_base,
        ec2_config_templates= ec2_config_templates,
        eks_config_templates=  eks_config_templates,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region= aws_region,
        local_pem_path = local_pem_path
    )

    try:
        # Initial state , read yaml file and update system variables
        logging.info(f" ===== Menu State: {fsm.state} =======")
        fsm.trigger_initial() 
        action = fsm.get_action()
        platform = fsm.get_platform()
        print(f"action :{action} platform:{platform}")
        logging.info(f" ===== Menu State: {fsm.state} =======")
    except Exception as e:
        fsm.trigger_end() 
        logging.error(f"Initial state error :{e}")
        return 
    
    if action == MenuActions.cleanup_cloud_resources.name:
        fsm.trigger_end() 
        
        return
    logging.info(f"action: {action}")

    if platform == Platform.LOCAL.name:
        try:
            fsm.trigger_run_local()
        except Exception as e:
            raise Exception(f"Run command in local failed: {e}")
    else:
        try:
            fsm.trigger_ready()
            logging.info(f" ===== Menu State: {fsm.state}  =======")
            fsm.trigger_process()
            logging.info(f" ===== Menu State: {fsm.state}  =======")
        except Exception as e:
            raise Exception(f"AWS platform error :{e}")
    

    try:
        fsm.trigger_end()
        logging.info(f" ===== Menu State: {fsm.state}  =======")
    except Exception as e:
        logging.error("End state error")
    return 
