
import click

from concurrent.futures import thread
from distutils.command.config import config
import json

from utils.ReadWriteIO import (read_yaml)
import io
import sys
import os
from utils.InvokeFunction import (
    invok_docekr_exec_run_process_files,
    invok_docekr_exec_run_process_all_files,
    invok_docekr_exec_run_process_first_n_files
    )
from typing import List

from multiprocessing.pool import ThreadPool as Pool
from threading import Timer
import asyncio
from models.SolarParams import SolarParams
from models.Config import Config
from models.Task import Task



def run_process_files(number):
    # import parametes from yaml
    solardata_parmas_obj = SolarParams.import_solar_params_from_yaml("./config/config.yaml")
    config_params_obj = Config.import_config_from_yaml("./config/config.yaml")


    if number is None:
        print("process default files in config.yaml")
        res = invok_docekr_exec_run_process_files(config_obj = config_params_obj,
                                        solarParams_obj= solardata_parmas_obj,
                                        container_type= config_params_obj.container_type, 
                                        container_name=config_params_obj.container_name)
        print(f"response : {res}")
    elif number == "n":
        print("process all files")
        res = invok_docekr_exec_run_process_all_files( config_params_obj,solardata_parmas_obj, config_params_obj.container_type, config_params_obj.container_name)
        print(f"response : {res}")
    else:
        if type(int(number)) == int:
            print(f"process first {number} files")
            res = invok_docekr_exec_run_process_first_n_files( config_params_obj,solardata_parmas_obj,number, config_params_obj.container_type, config_params_obj.container_name)
            print(f"response : {res}")
        else:
            print(f"error input {number}")
    
    return 


# Parent Command
@click.group()
def main():
	pass

# Run files 
@main.command()
@click.option('--number','-n',help="Process the first n files in bucket, if number=n, run all files in the bucket", default= None)
def run_files(number):
    """ Run Process Files"""
    run_process_files(number)


@main.command()
@click.argument('text')
def capitalize(text):
	"""Capitalize Text"""
	click.echo(text.upper())

if __name__ == '__main__':
	main()