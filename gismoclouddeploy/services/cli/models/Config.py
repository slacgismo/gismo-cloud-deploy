from urllib3 import Retry
from utils.ReadWriteIO import read_yaml

class Config(object):

    def __init__(self,
                 files,
                 bucket,
                 process_all_files,
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
                 scale_eks_nodes_wait_time 
                 ):

        self.files = files
        self.bucket = bucket
        self.process_all_files = process_all_files
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



    
    def import_config_from_yaml(file):
        config_params = read_yaml(file)

        config = Config(
            
            files = config_params["files_config"]["files"],
            process_all_files = config_params["files_config"]["process_all_files"],
            bucket = config_params["files_config"]["bucket"],
            column_names = config_params["files_config"]["column_names"],
            saved_bucket = config_params["output"]["saved_bucket"],
            saved_tmp_path = config_params["output"]["saved_tmp_path"],
            saved_target_path = config_params["output"]["saved__target_path"],
            saved_target_filename = config_params["output"]["saved__target_filename"],
            dynamodb_tablename = config_params["output"]["dynamodb_tablename"],
            saved_logs_target_path = config_params["output"]["saved_logs_target_path"],
            saved_logs_target_filename = config_params["output"]["saved_logs_target_filename"],
            environment = config_params["general"]["environment"],
            container_type = config_params["general"]["container_type"],
            container_name = config_params["general"]["container_name"],
            interval_of_check_task_status = config_params["general"]["interval_of_check_task_status"],
            interval_of_exit_check_status = config_params["general"]["interval_of_exit_check_status"],
            worker_replicas= config_params["k8s_config"]["worker_replicas"],
            interval_of_check_sqs_in_second= config_params["aws_config"]["interval_of_check_sqs_in_second"],
            interval_of_total_wait_time_of_sqs= config_params["aws_config"]["interval_of_total_wait_time_of_sqs"],
            eks_nodes_number = config_params["aws_config"]["eks_nodes_number"],
            scale_eks_nodes_wait_time =  config_params["aws_config"]["scale_eks_nodes_wait_time"],
            
        )
        return config

    def parse_config_to_json_str(self):

        str = "{" 
        str+= f" \"bucket\":\"{self.bucket}\"," 
        str+= f" \"process_all_files\":\"{self.process_all_files}\"," 
        str+= f" \"files\":\"{self.files}\"," 
        str+= f" \"column_names\":\"{self.column_names}\"," 
        str+= f" \"saved_bucket\":\"{self.saved_bucket}\"," 
        str+= f" \"saved_tmp_path\":\"{self.saved_tmp_path}\"," 
        str+= f" \"saved_target_path\":\"{self.saved_target_path}\","
        str+= f" \"saved_target_filename\":\"{self.saved_target_filename}\"," 
        str+= f" \"dynamodb_tablename\":\"{self.dynamodb_tablename}\","
        str+= f" \"saved_logs_target_path\":\"{self.saved_logs_target_path}\","
        str+= f" \"saved_logs_target_filename\":\"{self.saved_logs_target_filename}\","
        str+= f" \"interval_of_check_task_status\":\"{self.interval_of_check_task_status}\","  
        str+= f" \"interval_of_exit_check_status\":\"{self.interval_of_exit_check_status}\""  
        str+="}"
        return str