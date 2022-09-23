import logging


def verify_keys_in_configfile(config_dict:dict):
    '''
     Verify Keys in config_file
    '''
    logging.info(f"Check if all keys exists in {config_dict}")
    try:
        verify_a_key_in_dict(dict_format=config_dict, key="scale_eks_nodes_wait_time")
        verify_a_key_in_dict(dict_format=config_dict, key="interval_of_wait_pod_ready")
        verify_a_key_in_dict(dict_format=config_dict, key="data_bucket")
        verify_a_key_in_dict(dict_format=config_dict, key="file_pattern")
        verify_a_key_in_dict(dict_format=config_dict, key="process_column_keywords")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_bucket")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_path_cloud")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_path_local")
        verify_a_key_in_dict(dict_format=config_dict, key="acccepted_idle_time")
        verify_a_key_in_dict(dict_format=config_dict, key="interval_of_checking_sqs")
        verify_a_key_in_dict(dict_format=config_dict, key="filename")
        verify_a_key_in_dict(dict_format=config_dict, key="repeat_number_per_round")
        verify_a_key_in_dict(dict_format=config_dict, key="is_celeryflower_on")
        logging.info("Verify config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert error {e}")



def verify_keys_in_ec2_configfile(config_dict:dict):

    try:
   
        assert 'ec2_image_id' in config_dict
        assert 'ec2_instance_id' in config_dict
        assert 'ec2_volume' in config_dict
        assert 'key_pair_name' in config_dict
        assert 'login_user' in config_dict
        assert 'tags' in config_dict
        assert 'SecurityGroupIds' in config_dict
        assert 'vpc_id' in config_dict

        logging.info("Verify ec2 config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert ec2 error {e}")


def verify_keys_in_eks_configfile(config_dict:dict):
    try:
        assert 'apiVersion' in config_dict
        assert 'metadata' in config_dict
        assert 'nodeGroups' in config_dict
        # assert 'services_config_list' in self._config
        # assert 'aws_config' in self._config


        # worker_config
        metadata = config_dict['metadata']
        assert 'name' in metadata
        assert 'region'in  metadata
        assert 'tags' in metadata
        # assert metadata['tags']['project'] != '<auto-generated>'

        nodeGroups = config_dict['nodeGroups']
        assert len(nodeGroups) > 0
        # assert nodeGroups[0]['tags']['project'] != '<auto-generated>'

        logging.info("Verify eks config key success")
    except AssertionError as e:
        raise AssertionError(f"Assert eks error {e}")


def verify_a_key_in_dict(dict_format:dict, key:str) -> None:
    try:
        assert key in dict_format
    except AssertionError:
        raise f"{dict_format} does not contain {key}"

def verify_solver(confg_dict:dict, key:str) -> None:
    '''
    verify solver exist
    '''
    if 'solver' in confg_dict:
        logging.warning("Solver is listed in config Verify solver file exist")
        try:
            solver_dict = confg_dict['solver']
            verify_a_key_in_dict(dict_format=solver_dict, key='solver_name')
            verify_a_key_in_dict(dict_format=solver_dict, key='solver_lic_local_path')
            verify_a_key_in_dict(dict_format=solver_dict, key='solver_lic_target_path')
            verify_a_key_in_dict(dict_format=solver_dict, key='solver_lic_file_name')
        except Exception as e:
            raise e
    else:
        logging.warning("Process without solver file")