import os
from pathlib import Path


class BaseConfig:
    """Base configuration"""
    BASE_DIR = Path(__file__).parent.parent

    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{BASE_DIR}/db.sqlite3')

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')

    SECRET_KEY = os.environ.get('SECRET_KEY')

    SOCKETIO_MESSAGE_QUEUE = os.environ.get(
        'SOCKETIO_MESSAGE_QUEUE',
        'redis://127.0.0.1:6379/0'
    )
    CELERY_BEAT_SCHEDULE = {
        'task-schedule-work': {
            'task': 'task_schedule_work',
            "schedule": 5.0,  # five seconds
        },
    }

class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}