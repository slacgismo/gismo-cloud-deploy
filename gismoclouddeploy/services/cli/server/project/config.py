import os
from pathlib import Path


class BaseConfig:
    """Base configuration"""

    BASE_DIR = Path(__file__).parent.parent

    TESTING = False

    CELERY_broker_url = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
    result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")
    BROKER_CONNECTION_RETRY = True
    BROKER_CONNECTION_MAX_RETRIES = 0


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
