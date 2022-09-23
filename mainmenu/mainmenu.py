from genericpath import exists
import imp
from importlib.resources import path
import coloredlogs, logging
from .classes.Menu import Menu

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

    menus.select_main_menus()

#     menus.select_main_menus()
#     # Initialization 