import time

from .classes.constants.DevEnvironments import DevEnvironments
from .classes.GismoCloudDeploy import GismoCloudDeploy

from .classes.utilities.check_aws import (
    check_environment_is_aws,
)
import logging


def gismoclouddeploy(
    number: int = 1,
    project: str = None,
    scale_nodes: int = 1,
    repeat: int = 1,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    ecr_repo: str = None,
    cluster: str = None,
    nodegroup_name: str = None,
    instance_type: str = None,
    default_fileslist: list = [],
) -> None:
    """
    Proccess files in defined bucket
    :param number:      number of first n files in bucket. Default value is `None`.
                        If number is None, this application process defined files in config.yaml.
                        If number is 0, this application processs all files in the defined bucket in config.yaml.
                        If number is an integer, this applicaion process the first `number` files in the defined bucket in config.yaml.

    :param scalenodes:  Define the number of nodes(instances) that you want to generate on AWS EKS or any cloud platform. The default number is `1`.
    :param project:     Define the project name. The default projec is `examples/sleep`.
    :param repeat:      Define how many times you want to repeat this process. The default number is `1`.
    :param cluster:     Define the cluster name of AWS EKS cluster. If you are running on local machine, you can use the default name `local`.
    :param nodegroup_name:  Define the nodegroup of cluster. The default name is `gcd`.
                            You should not change this parameters unless you change it in cluster.yaml when you create a new cluster.
    :param instance_type:   Define the instance type of the nodes. You should not change this parameters unless you change it in cluster.yaml when you create a new cluster.
                            (PS. t2.micro cannot work in this application.)
    :param file:        If you want to process specific files on S3 bucket, you can use this option command.
                        For example: python3 main.py run-files -f PVO/PVOutput/11106.csv -f PVO/PVOutput/10010.csv -s 1 -p examples/solardatatools -c <your-cluster-name>

    """

    env = DevEnvironments.LOCAL.name
    if check_environment_is_aws():
        env = DevEnvironments.AWS.name

    gcd = GismoCloudDeploy(
        project=project,
        num_inputfile=number,
        scale_nodes=scale_nodes,
        repeat=repeat,
        env=env,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
        ecr_repo=ecr_repo,
        instance_type=instance_type,
        nodegroup_name=nodegroup_name,
        cluster=cluster,
        default_fileslist=default_fileslist,
    )
    try:
        # Initial state , read yaml file and update system variables
        logging.info(f" ===== State: {gcd.state} =======")
        gcd.trigger_initial()
        num_repetition = gcd.get_num_repetition()
        repeat_index = gcd.get_repeat_index()
    except Exception as e:
        logging.error(f"Initial error :{e}")

    while repeat_index < num_repetition:
        try:
            logging.info(
                f" ===== State: {gcd.state} ; repeat index {repeat_index} ======="
            )
            # ready state, build , tag and push images
            gcd.trigger_ready()
            logging.info(
                f" ===== State: {gcd.state} ; repeat index {repeat_index} ======="
            )
            # deploy state, deploy k8s , scale eks nodes

            gcd.trigger_deploy()
            logging.info(
                f" ===== State: {gcd.state} ; repeat index {repeat_index} ======="
            )

            # processing state, send coammd to server, long pulling sqs
            gcd.trigger_processing()
            logging.info(
                f" ===== State: {gcd.state} ; repeat index {repeat_index} ======="
            )
            # trigger repetition, increate repeat index and update file index
            gcd.trigger_repetition()
            repeat_index = gcd.get_repeat_index()
            time.sleep(1)
        except Exception as e:
            # something wrong break while loop and clean services.
            logging.error(f"Somehting wrong : {e}")
            break

    # clean up state, clean up k8s, delete namspaces, scale down eks nodes to 0 .
    logging.info(f" ===== State: {gcd.state} =======")
    gcd.trigger_cleanup()
    logging.info(f" ===== State: {gcd.state} =======")
    return
