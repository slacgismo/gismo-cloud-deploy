from email.policy import default
import json
import logging
from telnetlib import STATUS

from project import create_app, ext_celery
from utils.aws_utils import connect_aws_client
from utils.find_matched_column_name_set import find_matched_column_name_set
from celery.result import AsyncResult
from flask.cli import FlaskGroup
import click
import time
from project.tasks import process_data_task, pong_worker
from project.tasks_utilities.tasks_utils import publish_message_sns, send_queue_message
from models.SNSSubjectsAlert import SNSSubjectsAlert

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

    try:
        worker_config_json = json.loads(worker_config_str)
    except Exception as e:
        logger.error(f"Parse worker config failed {e}")
        raise
    default_files = json.loads(worker_config_json["default_process_files"])
    sqs_url = worker_config_json["sqs_url"]
    po_server_name =  worker_config_json["po_server_name"]
    try:
        s3_client = connect_aws_client(
            client_name="s3",
            key_id=worker_config_json["aws_access_key"],
            secret=worker_config_json["aws_secret_access_key"],
            region=worker_config_json["aws_region"],
        )
        sqs_client = connect_aws_client(
            client_name="sqs",
            key_id=worker_config_json["aws_access_key"],
            secret=worker_config_json["aws_secret_access_key"],
            region=worker_config_json["aws_region"],
        )

    except Exception as e:
        logger.error(f"AWS validation failed {e}")
        return "AWS validation fail"

    # print(default_files)
    task_ids = []
    user_id = worker_config_json["user_id"]
    repeat_number_per_round = int(worker_config_json["repeat_number_per_round"])
    for i in range(repeat_number_per_round):
        for index_file, file in enumerate(default_files):
            if worker_config_json["data_file_type"] == ".csv":
                matched_column_set = find_matched_column_name_set(
                    bucket_name=worker_config_json["data_bucket"],
                    columns_key=worker_config_json["process_column_keywords"],
                    file_path_name=file,
                    s3_client=s3_client,
                )
            else:
                matched_column_set = {"None"}

            # print(f"matched_column_set {matched_column_set}")
            for index_colium,  column in enumerate(matched_column_set):
                task_input_json = worker_config_json
                task_input_json["curr_process_file"] = file
                task_input_json["curr_process_column"] = column
                task_input_json["po_server_name"] = po_server_name
                task_id = process_data_task.delay(**task_input_json)
                # print(f"======= task_id: {task_id}")
                task_ids.append(task_id)
                MSG_ATTRIBUTES = {
                    "user_id": {"DataType": "String", "StringValue": user_id},
                }
                send_time = time.time()
                # num_total_tasks = len(default_files)*len(matched_column_set)*repeat_number_per_round
                if i == repeat_number_per_round-1 and index_colium == len(matched_column_set) -1 and index_file == len(default_files) - 1:
                    num_total_tasks = len(task_ids)
                else:
                    num_total_tasks = 0 
                msg_body = {
                    "data": None,
                    "error": None,
                    "file_name": file,
                    "column_name": column,
                    "task_id": str(task_id),
                    "send_time": str(send_time),
                    "po_server_name":po_server_name,
                    "num_total_tasks":num_total_tasks,
                    "alert_type": SNSSubjectsAlert.SEND_TASKID.name,

                }
                MSG_BODY = json.dumps(msg_body)
                send_response = send_queue_message(
                    queue_url=sqs_url,
                    msg_attributes=MSG_ATTRIBUTES,
                    msg_body=MSG_BODY,
                    sqs_client=sqs_client,
                )

                time.sleep(0.02)
            # publish sns message
    # print("------------->")
    # MSG_ATTRIBUTES2 = {
    #     "user_id": {"DataType": "String", "StringValue": str(user_id)},
    # }

    # msg_body = {
    #     "data": None,
    #     "error": None,
    #     "total_tasks": len(task_ids),
    #     "alert_type": SNSSubjectsAlert.SEND_TASKID_INFO.name,
    # }
    # MSG_BODY = json.dumps(msg_body)
    # send_response = send_queue_message(
    #     queue_url=sqs_url,
    #     msg_attributes=MSG_ATTRIBUTES2,
    #     msg_body=MSG_BODY,
    #     sqs_client=sqs_client,
    # )

    return


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
