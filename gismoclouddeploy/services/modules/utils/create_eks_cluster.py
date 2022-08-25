import logging
from .invoke_function import exec_eksctl_create_cluster,exec_eksctl_delete_cluster
from .modiy_config_parameters import modiy_config_parameters
from os.path import exists

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


def create_eks_cluster(config_file:str, aws_access_key:str,aws_secret_access_key:str, aws_region:str) -> str:
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

    cluster_file = config_json['aws_config']['cluster_file']

    if not exists(cluster_file):
        logger.error(f"{cluster_file} does not exist")
        return 
    res = exec_eksctl_create_cluster(cluster_file=cluster_file)
    logger.info(res)
    return 


def delete_eks_cluster(config_file:str, aws_access_key:str,aws_secret_access_key:str, aws_region:str) -> str:
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

    cluster_file = config_json['aws_config']['cluster_file']

    if not exists(cluster_file):
        logger.error(f"{cluster_file} does not exist")
        return 
    res = exec_eksctl_create_cluster(cluster_file=cluster_file)
    logger.info(res)
    return 