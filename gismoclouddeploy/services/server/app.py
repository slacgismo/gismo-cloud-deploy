from curses import flash
from project import create_app, ext_celery,db
from flask.cli import FlaskGroup
from flask import jsonify
from project.users.models import User
from project.solardata.models import SolarData
import click
from celery.result import AsyncResult
import time

from project.solardata.tasks import (
    read_all_datas_from_solardata,
    save_data_from_db_to_s3_task,
    process_data_task
)


app = create_app()
celery = ext_celery.celery

cli = FlaskGroup(create_app=create_app)


@cli.command()
@click.argument('x', nargs=1)
@click.argument('y', nargs=1)
def power(x, y):
    print(int(x)**int(y))

@app.route("/")
def hello_world():
    return "Hello, World!"

@cli.command("hi")
def hi():
    print("hello world2")
    return "Hello, World!"

@cli.command("read_data_from_db")
def read_data_from_db():
    task = read_all_datas_from_solardata.delay()
    print(f"task id : {task.id}")


@cli.command("process_a_file")
@click.argument('bucket_name', nargs=1)
@click.argument('file_path', nargs=1)
@click.argument('file_name', nargs=1)
@click.argument('column_name', nargs=1)
@click.argument('solver', nargs=1)
def process_a_file(bucket_name,file_path,file_name,column_name,solver):
    start_time = time.time()
    task = process_data_task.apply_async(
        [bucket_name,
        file_path,
        file_name,
        column_name,
        start_time,
        solver])
    print(f"task id : {task.id}")




@cli.command("get_task_status")    
@click.argument('task_id', nargs=1)
def get_task_status(task_id):
    task_result = AsyncResult(task_id)
    result = [{
        "task_id":task_id,
        "task_status":task_result.status,
        "task_result":task_result.result
    }]
    # result = {
    #     "task_id": task_id,
    #     "task_status": task_result.status,
    #     "task_result": task_result.result
    # }
    # return jsonify(result), 200
    print(f"{result}")





# DB
@cli.command('recreate_db')
def recreate_db():
    db.drop_all()
    db.create_all()
    db.session.commit()


@cli.command('seed_db')
def seed_db():
    """Seeds the database."""
    db.session.add(User(
        email='admin@example',
        username='Admnin User',

    ))
    db.session.add(SolarData(
        task_id = "1231223da",
        bucket_name = "pv.insight.nrel",
        file_path = "PVO/PVOutput",
        file_name = "10059.csv",
        column_name = "Power(W)",
        process_time = 23.23,
        power_units = "W",
        length = 4.41,
        capacity_estimate = 5.28,
        data_sampling = 5,
        data_quality_score = 98.4,
        error_message = "this is test error message",
        capacity_changes = False,
        num_clip_points = 0,
        normal_quality_scores = True,
        data_clearness_score = 31.8,
        inverter_clipping = False,
        tz_correction = -1,
        time_shifts = False,
    ))

    db.session.add(SolarData(
        task_id = "asdaaaadsa",
        bucket_name = "pv.insight.nrel",
        file_path = "PVO/PVOutput",
        file_name = "10060.csv",
        column_name = "Power(W)",
        process_time = 23.23,
        power_units = "W",
        length = 4.41,
        capacity_estimate = 5.28,
        data_sampling = 5,
        data_quality_score = 98.4,
        error_message = "this is test error message",
        capacity_changes = False,
        num_clip_points = 0,
        normal_quality_scores = True,
        data_clearness_score = 31.8,
        inverter_clipping = False,
        tz_correction = -1,
        time_shifts = False,
    ))

    db.session.commit()

@app.cli.command("celery_worker")
def celery_worker():
    from watchgod import run_process
    import subprocess

    def run_worker():
        subprocess.call(
            ["celery", "-A", "app.celery", "worker", "--loglevel=info"]
        )

    run_process("./project", run_worker)

if __name__ == '__main__':
    cli()