import os
from pathlib import Path


class BaseConfig:
    """Base configuration"""

    BASE_DIR = Path(__file__).parent.parent

    TESTING = False

    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get(
        "CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0"
    )
    # CELERY_RESULT_BACKEND = None
    broker_connection_retry = True  #  retry whenever it fails
    broker_connection_max_retries = 0  # disable the retry limit.
    task_soft_time_limit = True
    task_track_started = True
    task_annotations = {"*": {"rate_limit": "10/s"}}
    task_acks_late = True
    # worker_prefetch_multiplier = 1
    CELERYD_PREFETCH_MULTIPLIER = 64


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
