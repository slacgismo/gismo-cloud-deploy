import os

from flask import Flask
from flask_celeryext import FlaskCeleryExt
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect  # new
from flask_cors import CORS  # new
from project.celery_utils import make_celery
from project.config import config


# instantiate the extensions
db = SQLAlchemy()
migrate = Migrate()
ext_celery = FlaskCeleryExt(create_celery_app=make_celery)
csrf = CSRFProtect()  # new
cors = CORS()  # new


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    # instantiate the app
    app = Flask(__name__)

    # set config
    app.config.from_object(config[config_name])

    # set up extensions
    db.init_app(app)
    migrate.init_app(app, db)
    ext_celery.init_app(app)
    csrf.init_app(app)  # new
    cors.init_app(app, resources={r"*": {"origins": "*"}})  # new


    from project.solardata import solardata_blueprint
    app.register_blueprint(solardata_blueprint)

    # shell context for flask cli
    @app.shell_context_processor
    def ctx():
        return {'app': app, 'db': db}

    return app