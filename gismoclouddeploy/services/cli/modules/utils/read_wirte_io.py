import yaml
import json

# Read YAML file
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s: %(levelname)s: %(message)s",
)

from server.models.Configurations import Configurations


def read_yaml(filename):
    try:
        with open(filename, "r") as stream:
            data_loaded = yaml.safe_load(stream)

            return data_loaded
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))


def import_yaml_and_convert_to_json_str(
    yaml_file: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
    sns_topic: str,
) -> str:
    try:
        temp_json = read_yaml(yaml_file)
        temp_json["aws_access_key"] = aws_access_key
        temp_json["aws_secret_access_key"] = aws_secret_access_key
        temp_json["aws_region"] = aws_region
        temp_json["sns_topic"] = sns_topic
        return json.dumps(temp_json)
    except Exception as e:
        raise e


def make_config_obj_from_yaml(
    yaml_file: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
    sns_topic: str,
) -> Configurations:
    try:
        config_params = read_yaml(filename=yaml_file)
    except Exception as e:
        logger.error(f"{yaml_file} file didn't exist: {e}")
        raise e
    try:
        config = Configurations(
            files=config_params["files_config"]["files"],
            selected_algorithm=config_params["files_config"]["selected_algorithm"],
            bucket=config_params["files_config"]["bucket"],
            column_names=config_params["files_config"]["column_names"],
            saved_bucket=config_params["output"]["saved_bucket"],
            saved_tmp_path=config_params["output"]["saved_tmp_path"],
            saved_target_path=config_params["output"]["saved_target_path"],
            saved_target_filename=config_params["output"]["saved_target_filename"],
            dynamodb_tablename=config_params["output"]["dynamodb_tablename"],
            saved_logs_target_path=config_params["output"]["saved_logs_target_path"],
            saved_logs_target_filename=config_params["output"][
                "saved_logs_target_filename"
            ],
            environment=config_params["general"]["environment"],
            container_type=config_params["general"]["container_type"],
            container_name=config_params["general"]["container_name"],
            interval_of_check_task_status=config_params["general"][
                "interval_of_check_task_status"
            ],
            interval_of_exit_check_status=config_params["general"][
                "interval_of_exit_check_status"
            ],
            worker_replicas=config_params["k8s_config"]["worker_replicas"],
            interval_of_check_sqs_in_second=config_params["aws_config"][
                "interval_of_check_sqs_in_second"
            ],
            interval_of_total_wait_time_of_sqs=config_params["aws_config"][
                "interval_of_total_wait_time_of_sqs"
            ],
            cluster_name=config_params["aws_config"]["cluster_name"],
            nodegroup_name=config_params["aws_config"]["nodegroup_name"],
            eks_nodes_number=config_params["aws_config"]["eks_nodes_number"],
            scale_eks_nodes_wait_time=config_params["aws_config"][
                "scale_eks_nodes_wait_time"
            ],
            # aws credentail from environment in main
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            sns_topic=sns_topic,
        )
        return config
    except Exception as e:
        logger.error(
            f"solardata parameters format in {yaml_file} file is incorrect: {e}"
        )
        raise e
