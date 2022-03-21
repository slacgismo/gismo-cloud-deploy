from flask import Blueprint

users_blueprint = Blueprint("users", __name__, url_prefix="/users", template_folder="templates")

from . import models, tasks,views # noqa