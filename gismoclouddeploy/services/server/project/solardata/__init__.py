from .models import SolarData
from flask import Blueprint

solardata_blueprint = Blueprint("solardata", __name__, url_prefix="/solardata", template_folder="templates")

from . import models,tasks, tasks
