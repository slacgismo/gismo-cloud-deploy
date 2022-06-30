from .check_aws import check_aws_validity, check_environment_is_aws
from os.path import exists
import logging
import yaml
import os
import socket

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def modiy_config_parameters(
    configfile: str = "config.yaml",
    nodesscale: int = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    sqs_url: str = None,
    sns_topic: str = None,
    dlq_url: str = None,
    ecr_repo: str = None,
) -> str:

    try:
        check_aws_validity(key_id=aws_access_key, secret=aws_secret_access_key)
    except Exception as e:
        logger.error(f"AWS credential failed: {e}")
        return

    # check config exist
    config_yaml = f"./config/{configfile}"

    if exists(config_yaml) is False:
        logger.warning(
            f"./config/{configfile} not exist, use default config.yaml instead"
        )
        config_yaml = f"./config/config.yaml"

    """
    Generated unique file name and folder to save data, logs, solver's lic and plot
    """

    config_json = convert_yaml_to_json(yaml_file=config_yaml)
    user_id = str(socket.gethostname())
    if nodesscale is not None and check_environment_is_aws():
        logger.info(f"Update nodes eks and worker replicas to{nodesscale}")
        config_json["aws_config"]["eks_nodes_number"] = int(nodesscale)
        config_json["services_config_list"]["worker"]["desired_replicas"] = int(
            nodesscale
        )

    config_json["worker_config"]["user_id"] = user_id
    config_json["worker_config"]["solver"]["saved_temp_path_in_bucket"] = (
        config_json["worker_config"]["solver"]["saved_temp_path_in_bucket"]
        + "/"
        + user_id
    )
    config_json["worker_config"]["saved_rumtime_image_name"] = f"gantt-{user_id}.png"
    config_json["worker_config"][
        "saved_performance_file"
    ] = f"performance-{user_id}.txt"
    config_json["worker_config"]["saved_data_target_filename"] = f"data-{user_id}.csv"
    config_json["worker_config"]["saved_logs_target_filename"] = f"logs-{user_id}.csv"
    config_json["worker_config"]["saved_error_target_filename"] = f"error-{user_id}.csv"
    config_json["aws_config"]["aws_access_key"] = aws_access_key
    config_json["aws_config"]["aws_secret_access_key"] = aws_secret_access_key
    config_json["aws_config"]["aws_region"] = aws_region
    config_json["aws_config"]["sns_topic"] = sns_topic
    config_json["aws_config"]["sqs_url"] = sqs_url
    config_json["aws_config"]["dlq_url"] = dlq_url
    config_json["aws_config"]["ecr_repo"] = ecr_repo

    # check if local path exist
    result_local_folder = config_json["worker_config"]["saved_path_local"]
    if os.path.isdir(result_local_folder) is False:
        logger.info(f"Create local {result_local_folder} path")
        os.mkdir(result_local_folder)

    # local
    config_json["worker_config"]["save_data_file_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_data_target_filename"]
    )

    config_json["worker_config"]["save_logs_file_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_logs_target_filename"]
    )

    config_json["worker_config"]["save_error_file_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_error_target_filename"]
    )

    config_json["worker_config"]["save_plot_file_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_rumtime_image_name"]
    )

    config_json["worker_config"]["save_performance_local"] = (
        result_local_folder
        + "/"
        + config_json["worker_config"]["saved_performance_file"]
    )

    # aws
    config_json["worker_config"]["save_data_file_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_data_target_filename"]
    )

    config_json["worker_config"]["save_logs_file_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_logs_target_filename"]
    )

    config_json["worker_config"]["save_error_file_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_error_target_filename"]
    )

    config_json["worker_config"]["save_plot_file_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_rumtime_image_name"]
    )

    config_json["worker_config"]["save_performance_aws"] = (
        config_json["worker_config"]["saved_path_aws"]
        + "/"
        + config_json["worker_config"]["saved_performance_file"]
    )

    return config_json


def convert_yaml_to_json(yaml_file: str = None):
    try:
        with open(yaml_file, "r") as stream:
            config_json = yaml.safe_load(stream)
        return config_json
    except IOError as e:
        raise f"I/O error:{e}"
