import os

from flask import current_app, render_template

from . import solardata_blueprint
from project import db
from project.solardata.models import SolarData
import boto3
import time

@solardata_blueprint.route('/health/', methods=('GET',))
def health_check():
    return "Okay"