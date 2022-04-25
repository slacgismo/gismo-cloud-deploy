from project import create_app, ext_celery,db
from flask.cli import FlaskGroup
from project.users.models import User
from project.solardata.models import SolarData

app = create_app()
celery = ext_celery.celery

cli = FlaskGroup(create_app=create_app)

@app.route("/")
def hello_world():
    return "Hello, World!"

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