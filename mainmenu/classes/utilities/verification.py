import logging
from .convert_yaml import convert_yaml_to_json
from os.path import exists

def verify_keys_in_configfile(config_dict:dict):
    '''
     Verify Keys in config_file
    '''
    try:
        verify_a_key_in_dict(dict_format=config_dict, key="scale_eks_nodes_wait_time")
        verify_a_key_in_dict(dict_format=config_dict, key="interval_of_wait_pod_ready")
        verify_a_key_in_dict(dict_format=config_dict, key="data_bucket")
        verify_a_key_in_dict(dict_format=config_dict, key="file_pattern")
        verify_a_key_in_dict(dict_format=config_dict, key="process_column_keywords")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_bucket")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_path_cloud")
        verify_a_key_in_dict(dict_format=config_dict, key="acccepted_idle_time")
        verify_a_key_in_dict(dict_format=config_dict, key="interval_of_checking_sqs")
        verify_a_key_in_dict(dict_format=config_dict, key="filename")
        verify_a_key_in_dict(dict_format=config_dict, key="repeat_number_per_round")
        verify_a_key_in_dict(dict_format=config_dict, key="is_celeryflower_on")
        # Solver
        verify_a_key_in_dict(dict_format=config_dict, key="solver_name")
        verify_a_key_in_dict(dict_format=config_dict, key="solver_lic_target_path_in_images_dest")
        verify_a_key_in_dict(dict_format=config_dict, key="solver_lic_file_local_source")
        logging.info("Verify config key success")
    except Exception as e:
        raise Exception(f"Assert error {e}")



def verify_keys_in_ec2_configfile(config_dict:dict):

    try:
        verify_a_key_in_dict(dict_format=config_dict, key="ec2_image_id")
        verify_a_key_in_dict(dict_format=config_dict, key="ec2_instance_id")
        verify_a_key_in_dict(dict_format=config_dict, key="ec2_volume")
        verify_a_key_in_dict(dict_format=config_dict, key="key_pair_name")
        verify_a_key_in_dict(dict_format=config_dict, key="login_user")
        verify_a_key_in_dict(dict_format=config_dict, key="tags")
        verify_a_key_in_dict(dict_format=config_dict, key="securitygroup_name")

        logging.info("Verify ec2 config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert ec2 error {e}")


def verify_keys_in_eks_configfile(config_dict:dict):
    try:
        verify_a_key_in_dict(dict_format=config_dict, key="apiVersion")
        verify_a_key_in_dict(dict_format=config_dict, key="metadata")
        verify_a_key_in_dict(dict_format=config_dict, key="nodeGroups")
        metadata = config_dict['metadata']
        verify_a_key_in_dict(dict_format=metadata, key="name")
        verify_a_key_in_dict(dict_format=metadata, key="region")
        verify_a_key_in_dict(dict_format=metadata, key="tags")
        nodeGroups = config_dict['nodeGroups']
        assert len(nodeGroups) > 0
        logging.info("Verify eks config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert eks error {e}")


def verify_a_key_in_dict(dict_format:dict, key:str) -> None:
    try:
        assert key in dict_format
    except Exception:
        raise Exception(f"does not contain {key}")



def import_and_verify_ec2_config(ec2_config_file:str) -> dict:
    logging.info(f"import from ec2 {ec2_config_file}")
    if ec2_config_file is None:
        raise Exception(f"saved_ec2_config_file is None") 
    if not exists(ec2_config_file):
        raise Exception("saved_ec2_config_file does not exist")
    try:
        config_dict = convert_yaml_to_json(yaml_file=ec2_config_file)
        verify_keys_in_ec2_configfile(config_dict=config_dict)
        return config_dict
    except Exception as e:
        raise e 

def import_and_verify_eks_config(saved_eks_config_file:str)-> dict:
    logging.info("import from eks")
    if saved_eks_config_file is None:
        raise Exception(f"saved_eks_config_file is None") 
    if not exists(saved_eks_config_file):
        raise Exception("saved_eks_config_file does not exist")
    try:
        config_dict = convert_yaml_to_json(yaml_file=saved_eks_config_file)
        verify_keys_in_eks_configfile(config_dict=config_dict)
        return config_dict
    except Exception as e:
        raise e