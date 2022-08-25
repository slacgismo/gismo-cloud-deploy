import logging
from .invoke_function import exec_eksctl_create_cluster,exec_eksctl_delete_cluster
from os.path import exists
# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def create_eks_cluster(cluster_file:str) -> str:
    if not exists(cluster_file):
        logger.error(f"{cluster_file} does not exist")
        return 
    res = exec_eksctl_create_cluster(cluster_file=cluster_file)
    logger.info(res)
    return 

def delete_eks_cluster(cluster_file:str) -> str:
    if not exists(cluster_file):
        logger.error(f"{cluster_file} does not exist")
        return 
    res = exec_eksctl_delete_cluster(cluster_file=cluster_file)
    logger.info(res)
    return 