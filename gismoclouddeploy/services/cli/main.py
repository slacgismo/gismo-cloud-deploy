import click
from os.path import exists
import logging
import os

import modules

from server.utils.aws_utils import check_aws_validity, connect_aws_client

from dotenv import load_dotenv

load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("aws_access_key")
AWS_SECRET_ACCESS_KEY = os.getenv("aws_secret_key")
AWS_DEFAULT_REGION = os.getenv("aws_region")
SQS_URL = os.getenv("SQS_URL")  # aws standard url
SNS_TOPIC = os.getenv("SNS_TOPIC")  # aws sns
DLQ_URL = os.getenv("DLQ_URL")  # dead letter queue url

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


# Parent Command
@click.group()
def main():
    pass


# ***************************
#  Run files
# ***************************


@main.command()
@click.option(
    "--number",
    "-n",
    help="Process the first n files in bucket, if number=0, run all files in the bucket",
    default=None,
)
@click.option(
    "--deletenodes",
    "-d",
    is_flag=True,
    help="Enbale or disable delet nodes after process, default is Ture. Set False to disable ",
)
@click.option(
    "--configfile",
    "-f",
    help="Assign config files, Default files is config.yaml under /config",
    default="config.yaml",
)
@click.option(
    "--rollout",
    "-r",
    is_flag=True,
    help="Rollout and restart of webapp and worker pod of kubernetes",
)
def run_files(number, deletenodes, configfile, rollout):
    """Run Process Files"""
    run_process_files(number, deletenodes, configfile, rollout)


# ***************************
#  Scale the eks nodes' number
# ***************************


@main.command()
@click.argument("min_nodes")
@click.option(
    "--configfile",
    "-f",
    help="Assign config files, Default files is config.yaml under /config",
    default="config.yaml",
)
def nodes_scale(min_nodes, configfile):
    """Increate or decrease nodes number"""
    logger.info(f"Scale nodes {min_nodes}")
    try:
        # config_obj = import_config_from_yaml(configfile)
        config_params_obj = modules.read_wirte_io.make_config_obj_from_yaml(
            file=f"./config/{configfile}",
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            sns_topic=SNS_TOPIC,
        )
    except Exception as e:
        return logger.error(e)
    modules.eks_utils.scale_nodes_and_wait(
        scale_node_num=min_nodes,
        counter=int(config_params_obj.scale_eks_nodes_wait_time),
        delay=1,
        config_params_obj=config_params_obj,
    )


# ***************************
#  Check eks node status
# ***************************


@main.command()
def check_nodes():
    """Check nodes status"""
    modules.command_utils.check_nodes_status()


# ***************************
#  Read process logs file
#  in S3 buckeet, and save gantt
#  plot locally
# ***************************


@main.command()
def processlogs():
    """Porcess logs.csv file on AWS"""
    try:
        config_params_obj = modules.read_wirte_io.make_config_obj_from_yaml(
            yaml_file="./config/config.yaml",
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            sns_topic=SNS_TOPIC,
        )

    except Exception as e:
        logger.error(f"Convert yaml  error:{e}")
        return
    modules.command_utils.process_logs_and_plot(config_params_obj=config_params_obj)


# ***************************
#  Read DLQ
# ***************************


@main.command()
@click.option("--empty", "-e", is_flag=True, help=" Empty DLQ after receive message")
def read_dlq(empty):
    """Read messages from dlq"""
    click.echo(f"Read DLQ from :{DLQ_URL}. Delete message: {empty}")
    modules.command_utils.print_dlq(
        delete_messages=empty,
        aws_key=AWS_ACCESS_KEY_ID,
        aws_secret_key=AWS_SECRET_ACCESS_KEY,
        aws_region=AWS_DEFAULT_REGION,
        dlq_url=DLQ_URL,
        wait_time=80,
        delay=0.5,
    )


def run_process_files(number, delete_nodes, configfile, rollout):
    """
    Proccess files in S3 bucket
    :param number: number of first n files in bucket
    :param delete_nodes: delete node after process files
    :param configfile: config file name
    """

    # check aws credential

    try:
        check_aws_validity(key_id=AWS_ACCESS_KEY_ID, secret=AWS_SECRET_ACCESS_KEY)
    except Exception as e:
        logger.error(f"AWS credential failed: {e}")
        return

    # check config exist
    config_yaml = f"./config/{configfile}"

    if exists(config_yaml) is False:
        logger.warning(
            f"./config/{configfile} not exist, use default config.yaml instead"
        )
        config_yaml = f"./config/config.yaml"

    try:
        config_params_obj = modules.read_wirte_io.make_config_obj_from_yaml(
            yaml_file=config_yaml,
            aws_access_key=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_region=AWS_DEFAULT_REGION,
            sns_topic=SNS_TOPIC,
        )

    except Exception as e:
        logger.error(f"Convert yaml  error:{e}")
        return

    try:
        modules.command_utils.check_environment_setup(
            config_params_obj=config_params_obj, rollout=rollout
        )
    except Exception as e:
        logger.error(f"Environemnt setup failed :{e}")
        return

    # clear sqs
    logger.info(" ========= Clean previous SQS ========= ")
    sqs_client = connect_aws_client(
        client_name="sqs",
        key_id=config_params_obj.aws_access_key,
        secret=config_params_obj.aws_secret_access_key,
        region=config_params_obj.aws_region,
    )
    modules.sqs.clean_previous_sqs_message(
        sqs_url=SQS_URL, sqs_client=sqs_client, wait_time=2, counter=60, delay=1
    )

    try:
        total_task_num = modules.command_utils.invoke_process_files_based_on_number(
            number=number, config_params_obj=config_params_obj, config_yaml=config_yaml
        )

    except Exception as e:
        logger.error(f"Invoke process files error:{e}")
        return

    thread = modules.TaskThread(
        threadID=1,
        name="sqs",
        counter=120,
        wait_time=2,
        sqs_url=SQS_URL,
        num_task=total_task_num,
        config_params_obj=config_params_obj,
        delete_nodes_after_processing=delete_nodes,
        dlq_url=DLQ_URL,
        key_id=config_params_obj.aws_access_key,
        secret_key=config_params_obj.aws_secret_access_key,
        aws_region=config_params_obj.aws_region,
    )
    thread.start()

    return


if __name__ == "__main__":
    main()
