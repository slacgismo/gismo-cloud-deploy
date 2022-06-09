from cmath import log
import logging

from project import create_app, ext_celery
from flask.cli import FlaskGroup

from models.Configurations import make_configurations_obj_from_str

# from models.Configure import make_configure_from_str

# from project.solardata.utils import connect_aws_client, find_matched_column_name_set
from project.utils.utils import connect_aws_client, find_matched_column_name_set
import click
import time
import os

import re
from project.tasks import process_data_task, loop_tasks_status_task

# from project.tasks import process_data_task, loop_tasks_status_task

from project.utils.utils import get_process_filenamef_base_on_command

app = create_app()
celery = ext_celery.celery

cli = FlaskGroup(create_app=create_app)

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

# ***************************
# Process first n files : first_n_files is integer
# Process all files  : first_n_files is 0
# Process define files : first_n_files is None
# ***************************


@cli.command("process_files")
@click.argument("config_params_str", nargs=1)
@click.argument("first_n_files", nargs=1)
def process_files(config_params_str: str, first_n_files: str):
    # logger.info(f"first_n_files {first_n_files } config {config_params_str} ")
    try:
        configure_obj = make_configurations_obj_from_str(config_params_str)
    except Exception as e:
        return f"Convert configuratios josn string failed: {e} "
    # connect to S3
    task_ids = []
    try:
        s3_client = connect_aws_client(
            client_name="s3",
            key_id=configure_obj.aws_access_key,
            secret=configure_obj.aws_secret_access_key,
            region=configure_obj.aws_region,
        )
    except Exception as e:
        return "AWS validation fail"
    try:

        logger.info(f"get process filesname {first_n_files} {configure_obj.files}")

        n_files = get_process_filenamef_base_on_command(
            first_n_files=first_n_files,
            bucket=configure_obj.bucket,
            default_files=configure_obj.files,
            s3_client=s3_client,
        )

    except Exception as e:
        return f"Get filenames error: {e}"

    for file in n_files:
        # implement partial match
        matched_column_set = find_matched_column_name_set(
            bucket_name=configure_obj.bucket,
            columns_key=configure_obj.column_names,
            file_path_name=file,
            s3_client=s3_client,
        )
        for column in matched_column_set:

            path, filename = os.path.split(file)
            prefix = path.replace("/", "-")
            # remove special characters
            postfix = re.sub(r'[\\/*?:"<>|()]', "", column)
            temp_saved_filename = f"{prefix}-{postfix}-{filename}"
            start_time = time.time()
            task_id = process_data_task.apply_async(
                [
                    configure_obj.selected_algorithm,
                    configure_obj.dynamodb_tablename,
                    configure_obj.bucket,
                    file,
                    column,
                    configure_obj.saved_bucket,
                    configure_obj.saved_tmp_path,
                    temp_saved_filename,
                    start_time,
                    configure_obj.algorithms,
                    configure_obj.aws_access_key,
                    configure_obj.aws_secret_access_key,
                    configure_obj.aws_region,
                    configure_obj.sns_topic,
                ]
            )

            task_ids.append(str(task_id))
    # loop the task status in celery task
    loop_tasks_status_task.apply_async(
        [
            configure_obj.interval_of_check_task_status,
            configure_obj.interval_of_exit_check_status,
            task_ids,
            configure_obj.saved_bucket,
            configure_obj.saved_tmp_path,
            configure_obj.saved_target_path,
            configure_obj.saved_target_filename,
            configure_obj.dynamodb_tablename,
            configure_obj.saved_logs_target_path,
            configure_obj.saved_logs_target_filename,
            configure_obj.aws_access_key,
            configure_obj.aws_secret_access_key,
            configure_obj.aws_region,
            configure_obj.sns_topic,
        ]
    )


@cli.command("revoke_task")
@click.argument("task_id", nargs=1)
def revoke_task(task_id: str):

    logger.info(f"====== revoke id {task_id} ======= ")
    celery.control.revoke(task_id, terminate=True, signal="SIGKILL")


@app.cli.command("celery_worker")
def celery_worker():
    from watchgod import run_process
    import subprocess

    def run_worker():
        subprocess.call(["celery", "-A", "app.celery", "worker", "--loglevel=info"])

    run_process("./project", run_worker)


if __name__ == "__main__":
    cli()
