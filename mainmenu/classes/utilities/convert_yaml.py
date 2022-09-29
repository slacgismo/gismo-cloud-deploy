
import yaml
import os


def convert_yaml_to_json(yaml_file: str = None):
    try:
        with open(yaml_file, "r") as stream:
            config_json = yaml.safe_load(stream)
        return config_json
    except IOError as e:
        raise f"I/O error:{e}"

def write_aws_setting_to_yaml(file:str,setting:dict):
    # check if directory exist
    check_if_path_exist_and_create(file)

    with open(file, 'w') as yaml_file:
        yaml.dump(setting, yaml_file, default_flow_style=False)

def check_if_path_exist_and_create(file:str):
    path, tail = os.path.split(file)
    local_path_isExist = os.path.exists(path)
    if local_path_isExist is False:
        print(f"{path} does not exist. Create path")
        os.mkdir(path)
        print(f"Create {path} success")



