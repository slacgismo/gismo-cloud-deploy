
import time

from transitions import Machine



from .GismoCloudDeploy import Environments, GismoCloudDeploy

from .check_aws import (

    check_environment_is_aws,

)


import logging



# logger config
# logger = logging.getLogger()
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
# )
import coloredlogs, logging
# coloredlogs.install()


def run_process_files(
    number: int = 1,
    project: str =None,
    scale_nodes : int = 1,
    repeat :int = 1,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    ecr_repo: str = None,
) -> None:
    """
    Proccess files in defined bucket
    :param number:      number of first n files in bucket. Default value is `None`.
                        If number is None, this application process defined files in config.yaml.
                        If number is 0, this application processs all files in the defined bucket in config.yaml.
                        If number is an integer, this applicaion process the first `number` files in the defined bucket in config.yaml.
    
    :param configfile:  Define config file name. Default value is "./config/config.yaml"
    """
    # check aws credential

    # remove all files in results
    # list all files in results folder
    # check config exist

    env = Environments.LOCAL.name
    if check_environment_is_aws():
         env = Environments.AWS.name

    gcd = GismoCloudDeploy(
        project=project,
        num_inputfile=number,
        scale_nodes= scale_nodes,
        repeat = repeat,
        env=env,
        aws_access_key=aws_access_key,
        aws_secret_access_key = aws_secret_access_key,
        aws_region = aws_region,
        ecr_repo=ecr_repo
        
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
            logging.info(f" ===== State: {gcd.state} ; repeat index {repeat_index} =======")
            # ready state, build , tag and push images
            gcd.trigger_ready()
            logging.info(f" ===== State: {gcd.state} ; repeat index {repeat_index} =======")
            # deploy state, deploy k8s , scale eks nodes
            gcd.trigger_deploy()
            logging.info(f" ===== State: {gcd.state} ; repeat index {repeat_index} =======")
            # processing state, send coammd to server, long pulling sqs
            gcd.trigger_processing()
            logging.info(f" ===== State: {gcd.state} ; repeat index {repeat_index} =======")
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
