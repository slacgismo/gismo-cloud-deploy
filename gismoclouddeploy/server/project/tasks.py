from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult


from project.tasks_utilities.decorators import tracklog_decorator

import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

from .entrypoint import entrypoint


@shared_task(bind=True)
def pong_worker(
    *args,
    **kwargs,
):
    return "ok"


@shared_task(bind=True)
@tracklog_decorator
def process_data_task(
    *args,
    **kwargs,
):

    solver_name = None
    solver_file = None
    try:
        data_bucket = kwargs["data_bucket"]
        curr_process_file = kwargs["curr_process_file"]
        curr_process_column = kwargs["curr_process_column"]
        aws_access_key = kwargs["aws_access_key"]
        aws_secret_access_key = kwargs["aws_secret_access_key"]
        aws_region = kwargs["aws_region"]
    except Exception as e:
        raise Exception(f"Input key error:{e}")
    try:
        if "solver" in kwargs:
            solver = kwargs["solver"]
            print(f"solver :{solver}")
            if solver is not None:
                if "solver_name" in solver:
                    solver_name = solver["solver_name"]
                if (
                    "solver_lic_target_path" in solver
                    and "solver_lic_file_name" in solver
                ):
                    solver_file = (
                        solver["solver_lic_target_path"]
                        + "/"
                        + solver["solver_lic_file_name"]
                    )
    except Exception as e:
        raise Exception(f"parse {kwargs} key error:{e}")

    response = entrypoint(
        data_bucket=data_bucket,
        curr_process_file=curr_process_file,
        curr_process_column=curr_process_column,
        solver_name=solver_name,
        solver_file=solver_file,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
    )
    return response
