from email.policy import default
import json
import logging
from telnetlib import STATUS

from project import create_app, ext_celery
from utils.aws_utils import connect_aws_client
from utils.app_utils import (
    get_process_filename_base_on_command,
    find_matched_column_name_set,
)
from celery.result import AsyncResult
from flask.cli import FlaskGroup
import click
import time
import os
import re
from project.tasks import process_data_task, loop_tasks_status_task, pong_worker

app = create_app()
celery = ext_celery.celery

cli = FlaskGroup(create_app=create_app)

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


@cli.command("ping_worker")
def ping_worker():
    task_id = pong_worker.delay()
    print(task_id)


@cli.command("check_task_status")
@click.argument("task_id", nargs=1)
def check_task_status(task_id: str = None):
    response = AsyncResult(id=str(task_id))
    status = response.state
    result = response.get()
    info = response.info
    if result is None:
        result = "None"
    if info is None:
        info = "None"
    result = {
        "task_id": task_id,
        "task_status": status,
        "task_result": result,
        "task_info": info,
    }
    print(str(result))


# ***************************
# Process first n files : first_n_files is integer
# Process all files  : first_n_files is 0
# Process define files : first_n_files is None
# ***************************


@cli.command("process_files")
@click.argument("worker_config_str", nargs=1)
@click.argument("first_n_files", nargs=1)
def process_files(worker_config_str: str, first_n_files: str):
    # logger.info("------------------")
    try:
        worker_config_json = json.loads(worker_config_str)
    except Exception as e:
        logger.error(f"Parse worker config failed {e}")
        raise
    default_files = json.loads(worker_config_json["default_process_files"])
    # print(default_files_str)
    try:
        s3_client = connect_aws_client(
            client_name="s3",
            key_id=worker_config_json["aws_access_key"],
            secret=worker_config_json["aws_secret_access_key"],
            region=worker_config_json["aws_region"],
        )
        # print(worker_config_json)
    except Exception as e:
        logger.error(f"AWS validation failed {e}")
        return "AWS validation fail"

    # print(default_files)
    task_ids = []
    for file in default_files:
        # print("==========")
        # print(file)
        matched_column_set = find_matched_column_name_set(
            bucket_name=worker_config_json["data_bucket"],
            columns_key=worker_config_json["process_column_keywords"],
            file_path_name=file,
            s3_client=s3_client,
        )
        # print(f"matched_column_set {matched_column_set}")
        for column in matched_column_set:
            task_input_json = worker_config_json
            task_input_json["curr_process_file"] = file
            task_input_json["curr_process_column"] = column
            task_id = process_data_task.delay(**task_input_json)
            task_ids.append(str(task_id))
            # print(column)
            # return str(task_id)
            # print(str(task_id))

            time.sleep(0.5)

    for id in task_ids:
        print(id)
    # logger.info(worker_config_str)
    # try:
    #     s3_client = connect_aws_client(
    #         client_name="s3",
    #         key_id=worker_config_json["aws_access_key"],
    #         secret=worker_config_json["aws_secret_access_key"],
    #         region=worker_config_json["aws_region"],
    #     )
    #     # print(worker_config_json)
    # except Exception as e:
    #     return "AWS validation fail"
    # task_ids = []
    # try:
    #     n_files = get_process_filename_base_on_command(
    #         first_n_files=first_n_files,
    #         bucket=worker_config_json["data_bucket"],
    #         default_files=worker_config_json["default_process_files"],
    #         s3_client=s3_client,
    #     )

    #     # logger.info(n_files)
    # except Exception as e:
    #     return f"Get filenames error: {e}"
    # for file in n_files:
    #     # implement partial match
    # matched_column_set = find_matched_column_name_set(
    #     bucket_name=worker_config_json["data_bucket"],
    #     columns_key=worker_config_json["process_column_keywords"],
    #     file_path_name=file,
    #     s3_client=s3_client,
    # )
    #     for column in matched_column_set:
    #         path, filename = os.path.split(file)
    #         prefix = path.replace("/", "-")
    #         # remove special characters
    #         postfix = re.sub(r'[\\/*?:"<>|()]', "", column)
    #         temp_saved_filename = f"{prefix}-{postfix}-{filename}"
    #         start_time = time.time()
    # task_input_json = worker_config_json
    # task_input_json["curr_process_file"] = file
    # task_input_json["curr_process_column"] = column
    # task_input_json["temp_saved_filename"] = temp_saved_filename
    # task_id = process_data_task.delay(**task_input_json)
    #         task_ids.append(str(task_id))
    #         print(task_id)
    # time.sleep(0.1)
    # loop task ids and check status
    # time.sleep(1)
    # loop_tasks_status_task.apply_async([task_ids], kwargs=worker_config_json)


@cli.command("revoke_task")
@click.argument("task_id", nargs=1)
def revoke_task(task_id: str):

    logger.info(f"====== revoke id {task_id} ======= ")
    celery.control.revoke(task_id, terminate=True, signal="SIGKILL")


@app.cli.command("get_celery_worker_status")
def get_celery_worker_status():
    ERROR_KEY = "ERROR"
    try:
        # from celery.task.control import inspect
        # insp = inspect()
        insp = celery.task.control.inspect()
        d = insp.stats()
        if not d:
            d = {ERROR_KEY: "No running Celery workers were found."}
    except IOError as e:
        from errno import errorcode

        msg = "Error connecting to the backend: " + str(e)
        if len(e.args) > 0 and errorcode.get(e.args[0]) == "ECONNREFUSED":
            msg += " Check that the RabbitMQ server is running."
        d = {ERROR_KEY: msg}
    except ImportError as e:
        d = {ERROR_KEY: str(e)}
    return d


if __name__ == "__main__":
    cli()
