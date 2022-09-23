



import logging
from wsgiref.handlers import read_environ
from .invoke_function import exec_eksctl_create_cluster,exec_eksctl_delete_cluster
from .modiy_config_parameters import modiy_config_parameters,convert_yaml_to_json
from .create_ec2 import check_if_ec2_ready_for_ssh,run_command_in_ec2_ssh,upload_file_to_sc2,ssh_upload_folder_to_ec2
from os.path import exists
import boto3
import os
from .check_aws import (
    connect_aws_client,
    check_environment_is_aws,
    connect_aws_resource,
)
# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)



def handle_run_files_ssh(
    config_file:str, 
    aws_access_key:str,
    aws_secret_access_key:str,
    aws_region:str,
    command:str,
):

    s3_client = connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )

    config_json = modiy_config_parameters(
            configfile=config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_client= s3_client,
        )


    ec2_client = connect_aws_client(
        client_name="ec2",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )


    ec2_bastion_saved_config_file  = config_json['aws_config']['ec2_bastion_saved_config_file']
    cluster_file = config_json['aws_config']['cluster_file']
    # # ec2_config_yaml = f"./config/{configfile}"

    if exists(ec2_bastion_saved_config_file) is False:
        logger.error(
            f"{ec2_bastion_saved_config_file} not exist, use default config.yaml instead"
        )
        return 


    ec2_json = convert_yaml_to_json(yaml_file=ec2_bastion_saved_config_file)
    key_pair_name = ec2_json['key_pair_name']
    pem_location = ec2_json['pem_location']
    ec2_instance_id = ec2_json['ec2_instance_id']
    pem_file=pem_location +"/"+key_pair_name+".pem"
    user_name = ec2_json['user_name']
    remote_base_path = f"/home/{user_name}/gismo-cloud-deploy/gismoclouddeploy/services"


    if pem_location is None or os.path.exists(pem_location) is None: 
        logger.error(f"{pem_location} does not exist")
        return 
    
    if key_pair_name is None:
        logger.error(f"{key_pair_name} does not exist. Please create key pair first")
        return 

    if check_environment_is_aws():
        # 
        logger.error("Current environemnt is AWS. Please use this command in your local machine. ")
    else:

        try:
            response = ec2_client.describe_instance_status(InstanceIds=[ec2_instance_id], IncludeAllInstances=True)
            state = response['InstanceStatuses'][0]['InstanceState']['Name']
            logger.info(f"Current instance satate: {state}")
            if state == 'stopped':
                logger.info(f"EC2 instance: {ec2_instance_id} is stopped. Start instance")
                ec2 = boto3.resource('ec2')
                res = ec2.instances.filter(InstanceIds = [ec2_instance_id]).start() #for start an ec2 instance
                instance = check_if_ec2_ready_for_ssh(instance_id=ec2_instance_id, wait_time=60, delay=5, pem_location=pem_file,user_name=user_name)

            # upload cluster file to EC2 bastion 

  
            # upload code-templates folder
            code_template_folder = config_json['worker_config']['code_template_folder']
            local_dir = f"./config/{code_template_folder}"
            localpath , file = os.path.split(cluster_file)
            remote_dir=f"{remote_base_path}"
            logger.info("-------------------")
            logger.info(f"upload code-tempate folder:{code_template_folder}")
            logger.info("-------------------")
            ssh_upload_folder_to_ec2(
                ec2_client=ec2_client,
                user_name=user_name,
                instance_id=ec2_instance_id,
                pem_location=pem_file,
                local_folder=local_dir,
                remote_folder=remote_base_path
            )
            logger.info(f"==== Start command :{command} ===== ")
            ssh_command = f"cd {remote_base_path} \n source ./venv/bin/activate\n export $( grep -vE \"^(#.*|\s*)$\" {remote_base_path}/.env ) \n {command} "
            # print(command)
            run_command_in_ec2_ssh(
                    user_name=user_name,
                    instance_id=ec2_instance_id,
                    command=ssh_command,
                    pem_location=pem_file,
                    ec2_client=ec2_client
             )

        except Exception :
            logger.error(f"Cannot find instance id{ec2_instance_id} or not in a state to start instance.")
            raise Exception 

        return 



    
# import paramiko
# import os
# class ExportPrepare(object):
#     def __init__(self):
#         pass

#     def sftp_con(self):
#         t = paramiko.Transport((self.ip, self.port))
#         t.connect(username=self.username, password=self.password)
#         return t

#  # Find all the directories you want to upload already in files.
    # def __get_all_files_in_local_dir(self, local_dir):
    #     all_files = list()

    #     if os.path.exists(local_dir):
    #         files = os.listdir(local_dir)
    #         for x in files:
    #             filename = os.path.join(local_dir, x)
    #             print ("filename:" + filename)
    #             # isdir
    #             if os.path.isdir(filename):
    #                 all_files.extend(self.__get_all_files_in_local_dir(filename))
    #             else:
    #                 all_files.append(filename)
    #         else:
    #             print ('{}does not exist'.format(local_dir))
    #     return all_files

#  # Copy a local file (localpath) to the SFTP server as remotepath
#     def sftp_put_dir(self):
#         try:
#             # Upload the local test directory to remote root / usr / below
#             local_dir = "c:/test"
#             remote_dir = "/root/usr/test"
            
#             t = self.sftp_con()
#             sftp = paramiko.SFTPClient.from_transport(t)
#             # sshclient
#             ssh = paramiko.SSHClient()
#             ssh.load_system_host_keys()
#             ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#             ssh.connect(self.ip, port=self.port, username=self.username, password=self.password, compress=True)
#             ssh.exec_command('rm -rf ' + remote_dir)
#             if remote_dir[-1] == '/':
#                 remote_dir = remote_dir[0:-1]
#             all_files = self.__get_all_files_in_local_dir(local_dir)
#             for x in all_files:
#                 filename = os.path.split(x)[-1]
#                 remote_file = os.path.split(x)[0].replace(local_dir, remote_dir)
#                 path = remote_file.replace('\\', '/')
#             # The MKDIR that creates the directory SFTP can also be used, but can't create a multi-level directory, so use SSH to create.
#                 tdin, stdout, stderr = ssh.exec_command('mkdir -p ' + path)
#                 print( stderr.read())
#                 remote_filename = path + '/' + filename
#                 print (u'Put files...' + filename)
#                 sftp.put(x, remote_filename)
#             ssh.close()
#         except Exception as e:
#             print(e)
 
 
# if __name__=='__main__':
#  export_prepare = ExportPrepare()
#  export_prepare.sftp_put_dir()