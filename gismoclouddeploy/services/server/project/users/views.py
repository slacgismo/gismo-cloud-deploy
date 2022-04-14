import random
import logging
import os

import requests
from celery.result import AsyncResult
from flask import Blueprint, render_template, flash, abort, request, Response, jsonify, current_app

from . import users_blueprint
from project import csrf, db
from project.users.forms import YourForm
from project.users.tasks import sample_task, task_process_notification
from project.users.models import User

def api_call(email):
    # used for testing a failed api call
    if random.choice([0, 1]):
        raise Exception('random processing error')

    # used for simulating a call to a third-party api
    requests.post('https://httpbin.org/delay/5')


@users_blueprint.route('/ping/', methods=['GET'])
def ping():
    return jsonify({
        'status': 'success',
        'message': 'pong!',
        'container_id': os.uname()[1]
    })


@users_blueprint.route('/allusers/', methods=['GET', 'POST'])
@csrf.exempt
def all_users():
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    if request.method == 'POST':
        post_data = request.get_json()
        username = post_data.get('username')
        email = post_data.get('email')
        db.session.add(User(username=username, email=email))
        db.session.commit()
        response_object['message'] = 'user added!'
    else:
        response_object['users'] = [user.to_json() for user in User.query.all()]
    return jsonify(response_object)

@users_blueprint.route('/form/', methods=('GET', 'POST'))
def subscribe():
    form = YourForm()
    if form.validate_on_submit():
        task = sample_task.delay(form.email.data)
        return jsonify({
            'task_id': task.task_id,
        })
    return render_template('form.html', form=form)


@users_blueprint.route('/task_status/', methods=('GET', 'POST'))
@csrf.exempt
def task_status():
    task_id = request.args.get('task_id')

    if task_id:
        task = AsyncResult(task_id)
        if task.state == 'FAILURE':
            error = str(task.result)
            response = {
                'state': task.state,
                'error': error,
            }
        else:
            response = {
                'state': task.state,
            }
        return jsonify(response)



@users_blueprint.route('/webhook_test/', methods=('POST', ))
@csrf.exempt
def webhook_test():
    if not random.choice([0, 1]):
        # mimic an error
        raise Exception()

    # blocking process
    requests.post('https://httpbin.org/delay/5')
    return 'pong'

@users_blueprint.route('/webhook_test2/', methods=('POST', ))
@csrf.exempt
def webhook_test_2():
   task = task_process_notification.delay()
   current_app.logger.info(task.id)
   return 'pong'