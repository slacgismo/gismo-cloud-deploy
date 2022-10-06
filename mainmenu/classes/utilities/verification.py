import logging
from .convert_yaml import convert_yaml_to_json
from os.path import exists


def verify_keys_in_configfile(config_dict: dict):
    """
    Verify they keys exists in configure dictionary.
    This configure dictionary must match config.yaml file
    1. scale_eks_nodes_wait_time
    2. interval_of_wait_pod_ready
    3. data_bucket
    4. file_pattern
    5. process_column_keywords
    6. saved_bucket
    7. saved_path_cloud
    8. acccepted_idle_time
    9. interval_of_checking_sqs
    10. filename
    11. repeat_number_per_round
    12. is_celeryflower_on
    13. solver_name
    14. solver_lic_target_path_in_images_dest
    15. solver_lic_file_local_source

    Parameters
    ----------
    :param dict config_dict: A dictionary  of ec2 configure
    """
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
        verify_a_key_in_dict(
            dict_format=config_dict, key="solver_lic_target_path_in_images_dest"
        )
        verify_a_key_in_dict(
            dict_format=config_dict, key="solver_lic_file_local_source"
        )
        logging.info("Verify config key success")
    except Exception as e:
        raise Exception(f"Assert error {e}")


def verify_keys_in_ec2_configfile(config_dict: dict):
    """
    Verify they keys exists in ec2 configure dictionary.
    This configure dictionary must match config-ec2.yaml file
    1. ec2_image_id
    2. ec2_instance_id
    3. ec2_volume
    4. login_user
    5. tags
    6. securitygroup_name

    Parameters
    ----------
    :param dict config_dict: A dictionary  of ec2 configure
    """
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


def verify_keys_in_eks_configfile(config_dict: dict):
    """
    Verify they keys exists in eks configure dictionary.
    This configure dictionary must match cluster.yaml file
    Keys:
    1. apiVersion
    2. metadata
    3. ['metadata']['name']
    4. ['metadata']['region']
    5. ['metadata']['tags']
    6. nodeGroups
    7. ['nodeGroups'][0]['name']

    Parameters
    ----------
    :param dict config_dict: A dictionary  of eks configure
    """

    try:
        verify_a_key_in_dict(dict_format=config_dict, key="apiVersion")
        verify_a_key_in_dict(dict_format=config_dict, key="metadata")
        verify_a_key_in_dict(dict_format=config_dict, key="nodeGroups")
        metadata = config_dict["metadata"]
        verify_a_key_in_dict(dict_format=metadata, key="name")
        verify_a_key_in_dict(dict_format=metadata, key="region")
        verify_a_key_in_dict(dict_format=metadata, key="tags")
        nodeGroups = config_dict["nodeGroups"]
        assert len(nodeGroups) > 0
        logging.info("Verify eks config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert eks error {e}")


def verify_a_key_in_dict(dict_format: dict, key: str) -> None:
    try:
        assert key in dict_format
    except Exception:
        raise Exception(f"does not contain {key}")


def import_and_verify_ec2_config(ec2_config_file: str) -> dict:
    """
    import a ec2 configure file and verfiy its keys

    Parameters
    ----------
    :params str ec2_config_file: a ec2 configure file path and name

    Return
    ------
    :return a dictionary
    """
    logging.info(f"import from ec2 {ec2_config_file}")
    if ec2_config_file is None:
        raise ValueError(f"saved_ec2_config_file is None")
    if not exists(ec2_config_file):
        raise FileNotFoundError("saved_ec2_config_file does not exist")
    try:
        config_dict = convert_yaml_to_json(yaml_file=ec2_config_file)
        verify_keys_in_ec2_configfile(config_dict=config_dict)
        return config_dict
    except Exception as e:
        raise e


def import_and_verify_eks_config(saved_eks_config_file: str) -> dict:
    """
    import a eks configure file and verfiy its keys

    Parameters
    ----------
    :params str saved_eks_config_file: a eks configure file path and name

    Return
    ------
    :return a dictionary
    """
    logging.info("import from eks")
    if saved_eks_config_file is None:
        raise ValueError(f"saved_eks_config_file is None")
    if not exists(saved_eks_config_file):
        raise FileNotFoundError("saved_eks_config_file does not exist")
    try:
        config_dict = convert_yaml_to_json(yaml_file=saved_eks_config_file)
        verify_keys_in_eks_configfile(config_dict=config_dict)
        return config_dict
    except Exception as e:
        raise e
