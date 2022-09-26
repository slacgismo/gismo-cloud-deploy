import inquirer
from asyncio import streams

import logging
from .aws_utitlties import connect_aws_client,check_bucket_exists_on_s3
import os
def convert_yes_no_to_bool(input:str) -> bool:
    if input.lower() == "yes":
        return True
    elif input.lower() =="no":
        return False
    else:
        raise ValueError(f"Unknow answer {input}")


def handle_yes_or_no_question(
    input_question:str,
    default_answer:str,
) -> bool:
    answer = default_answer
    
    while True:
        answer = str(input(f"{input_question} (default answer:{default_answer}) ") or default_answer)
       
        if answer.lower() not in ('yes', 'no'):
            print("Not an appropriate choice. please type 'yes' or 'no' !!!")
        else:
            break
        print(f"answer : {answer}")
    return convert_yes_no_to_bool(input=answer)


def handle_input_s3_bucket_question(
    input_question: str,
    default_answer: str,
    aws_access_key:str,
    aws_secret_access_key :str,
    aws_region:str,
) -> str:
    s3_client = connect_aws_client(
            client_name='s3',
            key_id=aws_access_key,
            secret= aws_secret_access_key,
            region=aws_region
        )
    bucket = default_answer
    while True:
        bucket = str(input(f"{input_question} :(default: {default_answer})") or default_answer)
        # check if databucke exists
        if not check_bucket_exists_on_s3(s3_client, bucket_name=bucket):
            logging.info(f"{bucket} does not exist")
        else:
            logging.info(f"Found {bucket}!!")
            break
    return bucket

def handle_input_number_of_process_files_question(
    input_question:str,
    default_answer:int,
) -> int:

    input_number = default_answer
    while True:
        input_number = int(input(f"{input_question} (default:{default_answer}) (must be an integer):") or default_answer)
        # check if databucke exists
        if not isinstance(input_number, int):
            logging.error(f"{input_number} is not an integer")
        elif int(input_number) < 0:
            logging.error(f"Number: {input_number} must be a postive integer.")
        else:
            break
    if input_number == 0:
        logging.info("Process all files in  data bucket")
    else:
        logging.info(f"Process first {input_number} files in  data bucket")
    return input_number


def handle_input_cloumn_name_question(
    input_question:str,
    default_answer:int,
) -> list:
    column_name = default_answer

def handle_input_number_of_scale_instances_question(
    input_question:str,
    default_answer:int,
    max_node: int
) -> int:
    input_number = default_answer
    while True:
        input_number = int(input(f"{input_question} (minimum is 1 and max is {max_node}) (default:{default_answer}):") or default_answer)
        if not isinstance(input_number,int): 
            logging.error(f"{input_number} is not an integer")
        elif int(input_number) < 1 or int(input_number) > int(max_node):
            logging.error(f"Input number must be within 1 to {max_node}")
        else:
            break
    return input_number


def hanlde_input_project_name_in_tag(
    input_question:str,
    default_answer:str
) -> str:
    project_name = ""
    while True:
        if default_answer is not None:
            project_name = str(input(f"{input_question}: default: {default_answer}") or default_answer)
        else:
            project_name = str(input(f"{input_question}: "))
        if len(project_name) < 3:
            logging.error(f"Project name : {project_name} is too short")
        else:
            break
    return project_name

def handle_input_project_path_question(
    input_question:str,
    default_answer:int,
) -> str:
    while True:
        project_path = str(input(f"{input_question}: {default_answer} path): ") or default_answer)
        project_path = project_path.replace("\'","")
        print(f"project_path :{project_path}")
        if not os.path.exists(project_path):
            raise Exception(f"project path: {project_path} does not exist!!")
        else:
            break

    return project_path

def select_is_breaking_ssh():
    inst_question = [
        inquirer.List('is_breaking',
                            message="breaking ssh ?",
                            choices=['yes','no'],
                        ),
        ]
    inst_answer = inquirer.prompt(inst_question)

    is_breaking_ssh = inst_answer["is_breaking"]
    return convert_yes_no_to_bool(input=is_breaking_ssh)
