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
                 environment,
                 container_type,
                 container_name,
                 interval_of_check_task_status,
                 interval_of_exit_check_status,
                 ):

        self.files = files
        self.bucket = bucket
        self.process_all_files = process_all_files
        self.column_names = column_names
        self.saved_bucket = saved_bucket
        self.saved_tmp_path = saved_tmp_path
        self.saved_target_path = saved_target_path
        self.saved_target_filename = saved_target_filename
        self.environment = environment
        self.container_type = container_type
        self.container_name = container_name
        self.interval_of_check_task_status = interval_of_check_task_status
        self.interval_of_exit_check_status = interval_of_exit_check_status

    
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
            environment = config_params["general"]["environment"],
            container_type = config_params["general"]["container_type"],
            container_name = config_params["general"]["container_name"],
            interval_of_check_task_status = config_params["general"]["interval_of_check_task_status"],
            interval_of_exit_check_status = config_params["general"]["interval_of_exit_check_status"]
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
        str+= f" \"interval_of_check_task_status\":\"{self.interval_of_check_task_status}\","  
        str+= f" \"interval_of_exit_check_status\":\"{self.interval_of_exit_check_status}\""  
        str+="}"
        return str