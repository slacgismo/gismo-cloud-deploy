
from flask import jsonify
from celery.signals import task_postrun
import requests
from celery import shared_task
from celery.utils.log import get_task_logger

import os
import boto3
import pandas as pd
import solardatatools
import asyncio
import numbers
from project.solardata.models import SolarData
from io import StringIO




logger = get_task_logger(__name__)

@shared_task()
def read_all_datas_from_solardata():
    from project import create_app
    from project.solardata.models import SolarData

    app = create_app()
    with app.app_context():
        solardata = [solardata.to_json() for solardata in SolarData.query.all()]
        logger.info(solardata)


   
@shared_task()
def save_data_from_db_to_s3_task(bucket_name,file_path,file_name, delete_data):
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import to_s3
    app = create_app() 
    with app.app_context():
        solardatas = [solardata.to_json() for solardata in SolarData.query.all()]
        # logger.info(solardatas)
   
        # convert josn to csv file and save to s3
        # current_app.logger.info(all_datas)
        df = pd.json_normalize(solardatas)
        csv_buffer=StringIO()
        df.to_csv(csv_buffer)
        content = csv_buffer.getvalue()
        try:
            logger.info(bucket_name,file_path,file_name)
            to_s3(bucket_name,file_path,file_name, content)
        except Exception as e:
            response_object = {
                'status': 'failed',
                'container_id': os.uname()[1],
                'error': str(e)
            }
        return response_object





@shared_task(bind=True)
def process_data_task(self, bucket_name,file_path,file_name,column_name,start_time,solver):
    response_object = {
        'status': 'success',
        'container_id': os.uname()[1]
    }
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import (
        process_solardata_tools
    )
    app = create_app() 
    with app.app_context():

        process_solardata_tools(bucket_name,file_path,file_name,column_name,solver,start_time, self.request.id)
        return True
        # s3_resource = connect_aws_client("s3")
        # df = read_csv_from_s3(bucket_name,file_path,file_name,s3_resource)
        # dh = solardatatools.DataHandler(df)
        # error_message = ""
        # try:
        #     dh.run_pipeline(power_col=column_name,solver=solver, verbose=False,)
        # except Exception as e:
        #     error_message += str(e)
        #     return False
        
        # length=float("{:.2f}".format(dh.num_days))
        # if dh.num_days >= 365:
        #     length = float("{:.2f}".format(dh.num_days / 365))

        # capacity_estimate = float("{:.2f}".format(dh.capacity_estimate))

        # power_units = str(dh.power_units)
        # if power_units == "W":
        #     capacity_estimate =float("{:.2f}".format( dh.capacity_estimate / 1000))
        # data_sampling = int(dh.data_sampling)
        # if dh.raw_data_matrix.shape[0] >1440:
        #     data_sampling = int(dh.data_sampling * 60)

        
        # data_quality_score =  float("{:.1f}".format( dh.data_quality_score * 100 ))


        # data_clearness_score = float("{:.1f}".format( dh.data_clearness_score * 100 ))
        # time_shifts = bool(dh.time_shifts)
        # num_clip_points = int( dh.num_clip_points )
        # tz_correction = int(dh.tz_correction)
        # inverter_clipping = bool(dh.inverter_clipping)
        # normal_quality_scores = bool(dh.normal_quality_scores)
        # capacity_changes = bool(dh.capacity_changes)
            
        # process_time = time.time() - float(start_time)
        # logger.info(f'process_data_task api call to process time {process_time}')
        # response_object = {
        #     'status': 'success',
        #     'task_id': self.request.id,
        #     'container_id': os.uname()[1]
        # }
        # solardata = SolarData(
        #             task_id=self.request.id,
        #             bucket_name=bucket_name,
        #             file_path=file_path,
        #             file_name=file_name,
        #             column_name=column_name,
        #             process_time=process_time,
        #             length=length,
        #             power_units=power_units,
        #             capacity_estimate=capacity_estimate,
        #             data_sampling=data_sampling,
        #             data_quality_score = data_quality_score,
        #             data_clearness_score = data_clearness_score,
        #             error_message=error_message,
        #             time_shifts=time_shifts,
        #             capacity_changes=capacity_changes,
        #             num_clip_points=num_clip_points,
        #             tz_correction =tz_correction,
        #             inverter_clipping = inverter_clipping,
        #             normal_quality_scores=normal_quality_scores,
        # )
        # transaction_solardata()
        # response_object['solardata'] = [solardata.to_json()]
        # logger.info(response_object)
        # return True




