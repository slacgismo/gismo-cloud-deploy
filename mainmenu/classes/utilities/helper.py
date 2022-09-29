


import os
from os.path import  basename, exists
import shutil
import logging
from ..constants.Platform import Platform

from mainmenu.classes.constants.Platform import Platform
def generate_project_name_from_project_path(project_path:str) -> str:
    project_name = "temp/"+ basename(project_path)
    return project_name


def get_absolute_paht_from_project_name(project_name:str, base_path:str) -> str:
    temp_project_absoult_path =  os.path.join(base_path,project_name)
    return temp_project_absoult_path


def delete_project_folder(project_path:str):

    if not os.path.exists(project_path):
        raise Exception(f"{project_path} does not exist")
    try:
        shutil.rmtree(project_path)
        logging.info(f"Delete {project_path} success")
    except Exception as e:
        raise Exception(f"Dlete {project_path} failded")

def get_pem_file_full_path_name(local_pem_path,key_pair_name):
    full_path = local_pem_path +f"/{key_pair_name}.pem"
    return full_path


def generate_run_command_from_inputs(
    process_first_n_files:int = 1, 
    cluster_name:str = None, 
    num_of_nodes:str = 1, 
    project_name:str = None, 
    platform:Platform= True) -> str:

    command = None
    if platform == Platform.LOCAL.name:
        command = f"python3 main.py run-files -n {process_first_n_files} -p {project_name}"
    elif platform == Platform.AWS.name:
        command = f"python3 main.py run-files -n {process_first_n_files} -s {num_of_nodes} -p {project_name} -c {cluster_name}"

    if command is None:
        raise Exception("Generated command is None")
        
    return command