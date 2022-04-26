from utils.ReadWriteIO import read_yaml

class Config(object):

    def __init__(self,
                 files,
                 bucket,
                 column_names,
                 saved_bucket,
                 saved_tmp_path,
                 saved_target_path,
                 saved_target_filename,
                 environment,
                 container_type,
                 container_name
                 ):
        self.files = files
        self.bucket = bucket
        self.column_names = column_names
        self.saved_bucket = saved_bucket
        self.saved_tmp_path = saved_tmp_path
        self.saved_target_path = saved_target_path
        self.saved_target_filename = saved_target_filename
        self.environment = environment
        self.container_type = container_type
        self.container_name = container_name
    
    def import_config_from_yaml(file):
        config_params = read_yaml(file)
        config = Config(
            files = config_params["files_config"]["files"],
            bucket = config_params["files_config"]["bucket"],
            column_names = config_params["files_config"]["column_names"],
            saved_bucket = config_params["output"]["saved_bucket"],
            saved_tmp_path = config_params["output"]["saved_tmp_path"],
            saved_target_path = config_params["output"]["saved__target_path"],
            saved_target_filename = config_params["output"]["saved__target_filename"],
            environment = config_params["general"]["environment"],
            container_type = config_params["general"]["container_type"],
            container_name = config_params["general"]["container_name"])
        return config

# gen_config =  read_yaml("./config/general.yaml")
# environment = gen_config['general']['environment']
# container_type = gen_config['general']['container_type']
# container_name = gen_config['general']['container_name']

# files_config = read_yaml("./config/run-files.yaml")
# files = files_config['files_config']['files']
# bucket = files_config['files_config']['bucket']
# column_names = files_config['files_config']['column_names']
# saved_bucket = files_config['output']['saved_bucket']

# saved_tmp_path = files_config['output']['saved_tmp_path']
# saved__target_path = files_config['output']['saved__target_path']
# saved__target_filename = files_config['output']['saved__target_filename']


# # final_saved_filename = files_config['output']['saved_filename']

# sdt_params = read_yaml("./config/sdt-params.yaml")
# solver = sdt_params['solardata']['solver']

# gen_config =  read_yaml("./config/general.yaml")
# environment = gen_config['general']['environment']
# container_type = gen_config['general']['container_type']
# container_name = gen_config['general']['container_name']
