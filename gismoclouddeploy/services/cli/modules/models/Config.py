from modules.utils.read_wirte_io import read_yaml
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s: %(levelname)s: %(message)s",
)


class Config(object):
    def __init__(
        self,
        files,
        bucket,
        column_names,
        saved_bucket,
        saved_tmp_path,
        saved_target_path,
        saved_target_filename,
        dynamodb_tablename,
        saved_logs_target_path,
        saved_logs_target_filename,
        environment,
        container_type,
        container_name,
        interval_of_check_task_status,
        interval_of_exit_check_status,
        worker_replicas,
        interval_of_check_sqs_in_second,
        interval_of_total_wait_time_of_sqs,
        eks_nodes_number,
        scale_eks_nodes_wait_time,
        cluster_name,
        nodegroup_name,
        aws_access_key,
        aws_secret_access_key,
        aws_region,
        sns_topic,
    ):

        self.files = files
        self.bucket = bucket
        self.column_names = column_names
        self.saved_bucket = saved_bucket
        self.saved_tmp_path = saved_tmp_path
        self.saved_target_path = saved_target_path
        self.saved_target_filename = saved_target_filename
        self.dynamodb_tablename = dynamodb_tablename
        self.saved_logs_target_path = saved_logs_target_path
        self.saved_logs_target_filename = saved_logs_target_filename
        self.environment = environment
        self.container_type = container_type
        self.container_name = container_name
        self.interval_of_check_task_status = interval_of_check_task_status
        self.interval_of_exit_check_status = interval_of_exit_check_status
        self.worker_replicas = worker_replicas
        self.interval_of_check_sqs_in_second = interval_of_check_sqs_in_second
        self.interval_of_total_wait_time_of_sqs = interval_of_total_wait_time_of_sqs
        self.eks_nodes_number = eks_nodes_number
        self.scale_eks_nodes_wait_time = scale_eks_nodes_wait_time
        self.cluster_name = cluster_name
        self.nodegroup_name = nodegroup_name
        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.sns_topic = sns_topic

    def import_config_from_yaml(
        file: str,
        aws_access_key: str,
        aws_secret_access_key: str,
        aws_region: str,
        sns_topic: str,
    ):
        try:
            config_params = read_yaml(filename=file)
        except Exception as e:
            logger.error(f"{file} file didn't exist: {e}")
            raise e
        try:
            config = Config(
                files=config_params["files_config"]["files"],
                bucket=config_params["files_config"]["bucket"],
                column_names=config_params["files_config"]["column_names"],
                saved_bucket=config_params["output"]["saved_bucket"],
                saved_tmp_path=config_params["output"]["saved_tmp_path"],
                saved_target_path=config_params["output"]["saved__target_path"],
                saved_target_filename=config_params["output"]["saved__target_filename"],
                dynamodb_tablename=config_params["output"]["dynamodb_tablename"],
                saved_logs_target_path=config_params["output"][
                    "saved_logs_target_path"
                ],
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
                f"solardata parameters format in {file} file is incorrect: {e}"
            )
            raise e

    def parse_config_to_json_str(self):

        str = "{"
        str += f' "bucket":"{self.bucket}",'
        str += f' "files":"{self.files}",'
        str += f' "column_names":"{self.column_names}",'
        str += f' "saved_bucket":"{self.saved_bucket}",'
        str += f' "saved_tmp_path":"{self.saved_tmp_path}",'
        str += f' "saved_target_path":"{self.saved_target_path}",'
        str += f' "saved_target_filename":"{self.saved_target_filename}",'
        str += f' "dynamodb_tablename":"{self.dynamodb_tablename}",'
        str += f' "saved_logs_target_path":"{self.saved_logs_target_path}",'
        str += f' "saved_logs_target_filename":"{self.saved_logs_target_filename}",'
        str += (
            f' "interval_of_check_task_status":"{self.interval_of_check_task_status}",'
        )
        str += (
            f' "interval_of_exit_check_status":"{self.interval_of_exit_check_status}",'
        )
        str += f' "aws_access_key":"{self.aws_access_key}",'
        str += f' "aws_secret_access_key":"{self.aws_secret_access_key}",'
        str += f' "aws_region":"{self.aws_region}",'
        str += f' "sns_topic":"{self.sns_topic}"'
        str += "}"
        return str
