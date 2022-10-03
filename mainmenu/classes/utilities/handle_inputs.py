import inquirer
import readline

from mainmenu.classes.constants.EKSInstanceType import EKSInstanceType

from ..constants.InputDescriptions import InputDescriptions
from ..constants.MenuActions import MenuActions
from ..constants.Platform import Platform
import logging
from .aws_utitlties import connect_aws_client, check_bucket_exists_on_s3
import os
from ..constants.EC2InstanceType import EC2InstanceType


def convert_yes_no_to_bool(input: str) -> bool:
    if input.lower() == "yes":
        return True
    elif input.lower() == "no":
        return False
    else:
        raise ValueError(f"Unknow answer {input}")


def handle_yes_or_no_question(
    input_question: str,
    default_answer: str,
) -> bool:
    answer = default_answer

    while True:
        answer = str(
            input(f"{input_question} (default answer:{default_answer}) ")
            or default_answer
        )

        if answer.lower() not in ("yes", "no"):
            print("Not an appropriate choice. please type 'yes' or 'no' !!!")
        else:
            break
        print(f"answer : {answer}")
    return convert_yes_no_to_bool(input=answer)


def handle_input_s3_bucket_question(
    input_question: str,
    default_answer: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> str:
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    bucket = default_answer
    while True:
        bucket = str(
            input(f"{input_question} :(default: {default_answer})") or default_answer
        )
        # check if databucke exists
        if not check_bucket_exists_on_s3(s3_client, bucket_name=bucket):
            logging.info(f"{bucket} does not exist")
        else:
            logging.info(f"Found {bucket}!!")
            break
    return bucket


def handle_input_number_of_process_files_question(
    input_question: str,
    default_answer: int,
) -> int:

    input_number = default_answer
    while True:
        input_number = int(
            input(f"{input_question} (default:{default_answer}) (must be an integer):")
            or default_answer
        )
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
    input_question: str,
    default_answer: int,
) -> list:
    column_name = default_answer


def handle_input_number_of_scale_instances_question(
    input_question: str = None,
    default_answer: int = 1,
    max_node: int = 100,
    min_node: int = 1,
) -> int:
    input_number = default_answer
    while True:
        input_number = int(
            input(
                f"{input_question} (minimum is {min_node} and max is {max_node}) (default:{default_answer}):"
            )
            or default_answer
        )
        if not isinstance(input_number, int):
            logging.error(f"{input_number} is not an integer")
        elif int(input_number) < 1 or int(input_number) > int(max_node):
            logging.error(f"Input number must be within {min_node} to {max_node}")
        else:
            break
    return input_number


def hanlde_input_project_name_in_tag(input_question: str, default_answer: str) -> str:
    project_name = ""
    while True:
        if default_answer is not None:
            project_name = str(
                input(f"{input_question}: default: {default_answer}") or default_answer
            )
        else:
            project_name = str(input(f"{input_question}: "))
        if len(project_name) < 3:
            logging.error(f"Project name : {project_name} is too short")
        else:
            break
    return project_name


def handle_input_project_path_question(
    input_question: str,
    default_answer: str,
) -> str:
    while True:
        project_path = str(
            input(f"{input_question}: {default_answer} path): ") or default_answer
        )
        project_path = project_path.replace("'", "")
        print(f"project_path :{project_path}")
        if not os.path.exists(project_path):
            raise Exception(f"project path: {project_path} does not exist!!")
        else:
            break

    return project_path


def select_is_breaking_ssh():
    inst_question = [
        inquirer.List(
            "is_breaking",
            message="breaking ssh ?",
            choices=["yes", "no"],
        ),
    ]
    inst_answer = inquirer.prompt(inst_question)

    is_breaking_ssh = inst_answer["is_breaking"]
    return convert_yes_no_to_bool(input=is_breaking_ssh)


def select_acions_menu(platform: str) -> str:
    """
    Select an action from a menu
    """
    logging.info("Main menus")
    menus_selection = []
    action = None
    if platform == Platform.LOCAL.name:
        inst_question = [
            inquirer.List(
                "action",
                message=InputDescriptions.select_an_action.value,
                choices=[MenuActions.run_in_local_machine.name],
            ),
        ]
        inst_answer = inquirer.prompt(inst_question)
        action = inst_answer["action"]

    elif platform == Platform.AWS.name:
        inst_question = [
            inquirer.List(
                "action",
                message=InputDescriptions.select_an_action.value,
                choices=[
                    MenuActions.create_cloud_resources_and_start.name,
                    MenuActions.resume_from_existing.name,
                    MenuActions.cleanup_cloud_resources.name,
                ],
            ),
        ]
        inst_answer = inquirer.prompt(inst_question)
        action = inst_answer["action"]

    logging.info(f"Set action : {action}")
    return action


def enter_the_working_project_path(default_project: str) -> str:
    """
    input project path

    """

    origin_project_path = handle_input_project_path_question(
        input_question=InputDescriptions.input_project_folder_questions.value,
        default_answer=default_project,
    )
    return origin_project_path


def select_platform() -> str:
    """
    Select a platform
    """
    inst_question = [
        inquirer.List(
            "select_platform",
            message="Select platform ?",
            choices=[Platform.LOCAL.name, Platform.AWS.name],
        ),
    ]
    inst_answer = inquirer.prompt(inst_question)

    platform = inst_answer["select_platform"]
    return platform


def handle_proecess_files_inputs_questions(
    action: MenuActions, default_answer: dict, platform: Platform
) -> dict:

    return_answer = {}

    if platform == Platform.AWS.name:
        try:
            logging.info("hanlde inputs on AWS")
            # action
            if action == MenuActions.cleanup_cloud_resources.name:
                logging.info("Clearn up resources, No inputs needs")
                return return_answer

            # project tags
            if action == MenuActions.create_cloud_resources_and_start.name:
                project_in_tags = hanlde_input_project_name_in_tag(
                    input_question=InputDescriptions.input_project_name_in_tags.value,
                    default_answer=default_answer["project_in_tags"],
                )
                # update answer
                return_answer["project_in_tags"] = project_in_tags

            # debug mode
            if (
                action == MenuActions.create_cloud_resources_and_start.name
                or action == MenuActions.resume_from_existing.name
            ):
                is_ssh = handle_yes_or_no_question(
                    input_question=InputDescriptions.is_debug_mode_questions.value,
                    default_answer=default_answer["is_ssh"],
                )
                return_answer["is_ssh"] = is_ssh
                if is_ssh is True:
                    return return_answer

                # number of generate nodes

                logging.info("Input the number of instances ")
                num_of_nodes = handle_input_number_of_scale_instances_question(
                    input_question=InputDescriptions.input_number_of_generated_instances_questions.value,
                    default_answer=default_answer["num_of_nodes"],
                    max_node=default_answer["max_node"],
                )
                return_answer["num_of_nodes"] = num_of_nodes
                logging.info(f"Number of generated instances:{num_of_nodes}")

                # is clean up after completion
                cleanup_resources_after_completion = handle_yes_or_no_question(
                    input_question=InputDescriptions.is_cleanup_resources_after_completion.value,
                    default_answer=default_answer["cleanup_resources_after_completion"],
                )
                return_answer[
                    "cleanup_resources_after_completion"
                ] = cleanup_resources_after_completion
        except Exception as e:
            raise Exception(f"Handle input AWS questions error:{e}")

    # accross platform questions. run-files command
    try:
        process_first_n_files = default_answer["process_first_n_files"]
        is_process_all_file = handle_yes_or_no_question(
            input_question=InputDescriptions.is_process_all_files_questions.value,
            default_answer=default_answer["is_process_all_file"],
        )
        if is_process_all_file is False:
            process_first_n_files = handle_input_number_of_process_files_question(
                input_question=InputDescriptions.input_the_first_n_files_questions.value,
                default_answer=process_first_n_files,
            )
            return_answer["process_first_n_files"] = process_first_n_files
            logging.info(f"Process first {process_first_n_files} files")
        else:
            process_first_n_files = 0
            return_answer["process_first_n_files"] = process_first_n_files
            logging.info(f"Process all files: -n {process_first_n_files}")
    except Exception as e:
        raise Exception(f"Handle generate run-file command error:{e}")

    return return_answer


def select_ec2_instance_type() -> str:
    ec2_instance_type = [
        inquirer.List(
            "type",
            message="Select EC2 instance type",
            choices=[
                EC2InstanceType.t2medium.value,
                EC2InstanceType.t2large.value,
            ],
        ),
    ]
    inst_answer = inquirer.prompt(ec2_instance_type)
    type = inst_answer["type"]
    return type


def select_eks_instance_type() -> str:
    eks_instance_type = [
        inquirer.List(
            "type",
            message="Select EKS instance type",
            choices=[
                # EKSInstanceType.t2small.value,
                EKSInstanceType.t2medium.value,
                EKSInstanceType.t2large.value,
            ],
        ),
    ]
    inst_answer = inquirer.prompt(eks_instance_type)
    type = inst_answer["type"]
    return type


def get_system_id_from_selected_history(saved_config_path_base: str) -> str:
    """
    Select created resource config files from a path
    """
    logging.info("select_created_cloud_config_files")

    config_lists = get_subfolder(parent_folder=saved_config_path_base)
    if len(config_lists) == 0:
        raise Exception(" No history data")
    questions = [
        inquirer.List(
            "dir",
            message=InputDescriptions.select_an_created_resources.value,
            choices=config_lists,
        ),
    ]

    inst_answer = inquirer.prompt(questions)
    answer = inst_answer["dir"]
    # select_absolute_history_path = saved_config_path_base + f"/{answer}"
    return answer


def get_subfolder(parent_folder) -> list:
    if not os.path.exists(parent_folder):
        raise Exception(f"{parent_folder} does not exis–t")
    config_lists = []

    for fullpath, j, y in os.walk(parent_folder):
        relative_path = remove_partent_path_from_absolute_path(
            parent_path=parent_folder, absolut_path=fullpath
        )
        print(f"relative_path :{relative_path}")
        if relative_path == ".":
            continue
        config_lists.append(relative_path)
    return config_lists


def remove_partent_path_from_absolute_path(parent_path, absolut_path) -> str:
    relative_path = os.path.relpath(absolut_path, parent_path)
    return relative_path


def handle_input_ssh_custom_command():
    custom_command = input(f"Please type your command: ")
    return custom_command


def handle_update_number_of_nodes(default_number: int) -> int:
    update_nodes_number = handle_input_number_of_scale_instances_question(
        input_question=InputDescriptions.is_update_numbder_of_nodes.value,
        min_node=default_number,
        default_answer=default_number,
    )
    return int(update_nodes_number)
