import random
import logging
import requests

from celery.signals import after_setup_logger
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.signals import task_postrun



logger = get_task_logger(__name__)


@shared_task
def divide(x, y):
    # from celery.contrib import rdb
    # rdb.set_trace()

    import time
    time.sleep(5)
    return x / y


@shared_task()
def sample_task(email):
    from project.users.views import api_call

    api_call(email)

@shared_task(bind=True)
def task_process_notification(self):
    try:
        if not random.choice([0, 1]):
            # mimic random error
            raise Exception()

        # this would block the I/O
        requests.post('https://httpbin.org/delay/5')
    except Exception as e:
        logger.error('exception raised, it would be retry after 5 seconds')
        raise self.retry(exc=e, countdown=5)

@shared_task()
def task_send_welcome_email(user_pk):
    from project import create_app
    from project.users.models import User

    app = create_app()
    with app.app_context():
        user = User.query.get(user_pk)
        logger.info(f'send email to {user.email} {user.id}')

@shared_task()
def get_all_users():
    from project import create_app
    from project.users.models import User

    app = create_app()
    with app.app_context():
        user = [user.to_json() for user in User.query.all()]
        logger.info(f"all user {user}")
