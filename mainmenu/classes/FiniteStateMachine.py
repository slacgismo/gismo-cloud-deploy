from .utilities.aws_utitlties import connect_aws_client, get_iam_user_name
from transitions import Machine
from .utilities.handle_inputs import (
    handle_yes_or_no_question,
    select_acions_menu,
    enter_the_working_project_path,
    select_platform,
    handle_proecess_files_inputs_questions,
    get_system_id_from_selected_history,
)
from .AWSServices import AWSServices
from gismoclouddeploy.gismoclouddeploy import gismoclouddeploy
import time
import os
from os.path import exists
import logging
import shutil
from terminaltables import AsciiTable
from mainmenu.classes.constants.AWSActions import AWSActions
from mainmenu.classes.constants.InputDescriptions import InputDescriptions
from .constants.MenuActions import MenuActions
from .constants.EKSActions import EKSActions
from .constants.EC2Actions import EC2Actions
from .constants.Platform import Platform
from .utilities.convert_yaml import convert_yaml_to_json
from .utilities.verification import (
    verify_keys_in_configfile,
    import_and_verify_ec2_config,
    import_and_verify_eks_config,
)
from .utilities.helper import (
    generate_project_name_from_project_path,
    get_absolute_paht_from_project_name,
    delete_project_folder,
    generate_run_command_from_inputs,
)

import sys

sys.path.append("../../gismoclouddeploy")


class FiniteStateMachine(object):
    """Class for implemeting state machine to run automation of gismoclouddeploy on different platform."""

    states = [
        "start",
        "init",
        "ready",
        "process",
        "end",
    ]

    default_answer = {
        "default_project": "examples/sleep",
        "project_in_tags": "pvinsight",
        "is_ssh": "no",
        "num_of_nodes": 1,
        "cleanup_resources_after_completion": "no",
        "is_process_all_file": "no",
        "process_first_n_files": 1,
        "num_of_nodes": 1,
        "max_node": 100,
    }

    def __init__(
        self,
        saved_config_path_base: str = None,
        ec2_config_templates: str = None,
        eks_config_templates: str = None,
        aws_access_key: str = None,
        aws_secret_access_key: str = None,
        aws_region: str = None,
        local_pem_path: str = None,
    ) -> None:
        self.saved_config_path_base = saved_config_path_base
        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.ec2_config_templates = ec2_config_templates
        self.eks_config_templates = eks_config_templates
        self.local_pem_path = local_pem_path

        # private variable
        self._action = None
        self._origin_project_path = None
        self._base_path = os.getcwd()
        self._project_name = None
        self._select_history_path = None

        self._system_id = None
        self._start_time = str(int(time.time()))

        self._ec2_config_dict = {}
        self._eks_config_dict = {}

        self._input_answers = {}
        self._aws_services = None
        self._platform = None

        # Define finite state machine

        self.machine = Machine(
            model=self,
            states=FiniteStateMachine.states,
            initial="start",
            on_exception="handle_error",
            send_event=True,
        )
        # regular cloud state
        self.machine.add_transition(
            trigger="trigger_initial",
            source="start",
            dest="init",
            before="handle_inputs",
            after="handle_confirmation",
        )
        self.machine.add_transition(
            trigger="trigger_ready",
            source="init",
            dest="ready",
            before="handle_create_resources",
            after="handle_system_check",
        )
        self.machine.add_transition(
            trigger="trigger_process",
            source="ready",
            dest="process",
            after="handle_process",
        )

        # run in local machine
        self.machine.add_transition(
            trigger="trigger_run_local",
            source="init",
            dest="process",
            after="handle_local_processing",
        )

        # End of application
        self.machine.add_transition(
            trigger="trigger_end",
            source="*",
            dest="end",
            before="handle_cleanup_cloud_resources",
            after="handle_completion",
        )

    def _set_user_id(self):
        sts_client = connect_aws_client(
            client_name="sts",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        arn_user_name = get_iam_user_name(sts_client=sts_client)
        if arn_user_name is not None:
            return arn_user_name
        else:
            raise Exception("AWS credentials are not correct")

    def _generate_system_id(self):
        user_id = self._set_user_id()
        return f"gcd-{user_id}"

    def get_action(self):
        return self._action

    def get_platform(self):
        return self._platform

    # ==============
    # state function
    # ==============

    # Error state
    def handle_error(self, event):
        # logging.error("Error state")
        # ask if need to clean up the resources
        logging.error(f"Handle error :{event.error}")

        raise Exception(f"Error :{event.error}")

    # Init state
    def handle_inputs(self, event):
        logging.info("handle inputs")
        # step 1 input project folder
        self._origin_project_path = enter_the_working_project_path(
            default_project=FiniteStateMachine.default_answer["default_project"]
        )
        self.set_project_name()
        self.copy_origin_project_into_temp_folder()

        # step 2 verify project
        self.handle_verify_project_folder()
        # step 3 select platform
        self._platform = select_platform()
        # step 4 select action
        self._action = select_acions_menu(platform=self._platform)
        # step 5 ask inputs based on platform
        self._input_answers = handle_proecess_files_inputs_questions(
            action=self._action,
            platform=self._platform,
            default_answer=FiniteStateMachine.default_answer,
        )
        # step 6 import config or generate id on AWS
        if self._platform == Platform.AWS.name:
            if self._action == MenuActions.create_cloud_resources_and_start.name:
                logging.info("Generate system id")
                try:
                    self._ec2_config_dict = import_and_verify_ec2_config(
                        ec2_config_file=self.ec2_config_templates
                    )
                    self._eks_config_dict = import_and_verify_eks_config(
                        saved_eks_config_file=self.eks_config_templates
                    )
                    logging.info("==============")
                    # generate parameters and replace template dict
                    # generate ec2 and eks cluster name
                    self._system_id = self._generate_system_id()
                    cluster_name = self._system_id
                    keypair_name = self._system_id
                    if self._system_id is None or self._start_time is None:
                        raise Exception("system id or start time is None")

                    project_in_tags = self._input_answers["project_in_tags"]

                    # replace ec2 config
                    try:
                        self._ec2_config_dict["key_pair_name"] = keypair_name
                        ec2_project_tags = {"Key": "project", "Value": project_in_tags}
                        ec2_name_tags = {"Key": "Name", "Value": self._system_id}
                        # append tags
                        self._ec2_config_dict["tags"].append(ec2_project_tags)
                        self._ec2_config_dict["tags"].append(ec2_name_tags)

                        # replace eks config
                        self._eks_config_dict["metadata"]["name"] = cluster_name
                        self._eks_config_dict["metadata"]["region"] = self.aws_region
                        self._eks_config_dict["metadata"]["tags"][
                            "project"
                        ] = project_in_tags
                        self._eks_config_dict["nodeGroups"][0]["tags"][
                            "project"
                        ] = project_in_tags
                        logging.info(
                            "Generate ec2, eks parameters from templates success"
                        )
                    except Exception as e:
                        raise Exception(f"generate ec2 eks parameters failed:{e}")

                except Exception as e:
                    raise Exception(f"create cloud resources init failed:{e}")

            else:
                # select history
                logging.info("Import from hoistory base on system id")
                self._system_id = get_system_id_from_selected_history(
                    saved_config_path_base=self.saved_config_path_base
                )
                logging.info(f"selected id :{self._system_id }")
                self._select_history_path = (
                    self.saved_config_path_base + f"/{ self._system_id}"
                )

                ec2_config_file = self._select_history_path + "/config-ec2.yaml"

                try:
                    self._ec2_config_dict = import_and_verify_ec2_config(
                        ec2_config_file=ec2_config_file
                    )
                    tags = self._ec2_config_dict["tags"]
                except Exception as e:

                    raise Exception(f"Import and verify history ec2 file failed: {e}")
                eks_config_file = self._select_history_path + "/cluster.yaml"
                if not exists(eks_config_file):
                    logging.warning(
                        "No saved eks condig file found import from templates"
                    )
                    eks_config_file = self.eks_config_templates
                try:
                    self._eks_config_dict = import_and_verify_eks_config(
                        saved_eks_config_file=eks_config_file
                    )
                except Exception as e:
                    raise Exception("A EC2 file exists but a eks file does not exists")

        return

    def handle_confirmation(self, event):
        logging.info("handle confirmation")
        # step 1 print out variables
        if self._platform == Platform.AWS.name:
            # eks parameters
            ec2_arrays = [["EC2 setting", "Details"]]
            for key, value in self._ec2_config_dict.items():
                array = [key, value]
                ec2_arrays.append(array)
            ec2_table = AsciiTable(ec2_arrays)
            print(ec2_table.table)
            # ec2 parameters

            eks_arrays = [["EKS setting", "Details"]]
            for key, value in self._eks_config_dict.items():
                array = [key, value]
                eks_arrays.append(array)
            eks_table = AsciiTable(eks_arrays)
            print(eks_table.table)

        # general questions
        input_arrays = [["Input parameters", "answer"]]

        for key, value in self._input_answers.items():
            array = [key, value]
            input_arrays.append(array)
        # input_arrays.append(["run_files command",self._run_files_command])
        input_table = AsciiTable(input_arrays)

        print(input_table.table)
        # step 2 ask confirmation
        is_comfirm = handle_yes_or_no_question(
            input_question="Confirm to process (must be yes/no)", default_answer="yes"
        )
        if is_comfirm is False:
            raise Exception("Cancel process")
        # steo 3 init services based on system id and paltform
        if self._platform == Platform.AWS.name:
            temp_project_absoult_path = get_absolute_paht_from_project_name(
                project_name=self._project_name, base_path=self._base_path
            )
            logging.info("-----------------------------------------")
            logging.info(f"Init aws services {self._ec2_config_dict}")

            try:
                self._aws_services = AWSServices(
                    local_pem_path=self.local_pem_path,
                    aws_access_key=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_access_key,
                    aws_region=self.aws_region,
                    local_temp_project_path=temp_project_absoult_path,
                    project_name=self._project_name,
                    origin_project_path=self._origin_project_path,
                    system_id=self._system_id,
                    ec2_config_dict=self._ec2_config_dict,
                    eks_config_dict=self._eks_config_dict,
                )
            except Exception as e:
                raise Exception(f"Init aws service failed:{e}")

        return

    # Ready state
    def handle_create_resources(self, event):
        logging.info("handle_create_resources")
        if self._platform == Platform.AWS.name:
            if self._action == MenuActions.create_cloud_resources_and_start.name:
                logging.info("Start to create cloud resource")
                try:
                    self._aws_services.create_ec2_from_template_file()
                    export_ec2_file = (
                        self.saved_config_path_base
                        + f"/{self._system_id}/config-ec2.yaml"
                    )
                    self._aws_services.export_ec2_params_to_file(
                        export_file=export_ec2_file
                    )
                except Exception as e:
                    raise Exception(f"create ec2 failed: {e}")
                # step 5 , install dependencies
                try:
                    self._aws_services.hanle_ec2_setup_dependencies()
                except Exception as e:
                    raise Exception(f"setup ec2 failed :{e}")
                # create eks
                created_eks_config_file = (
                    self.saved_config_path_base + f"/{self._system_id}/cluster.yaml"
                )
                self._aws_services.generate_eks_config_and_export(
                    eks_config_yaml_dcit=self._eks_config_dict,
                    export_file=created_eks_config_file,
                )
                # upload local cluster file to cloud
                try:
                    self._aws_services.ssh_update_eks_cluster_file(
                        src_file=created_eks_config_file
                    )
                except Exception as e:
                    raise Exception(f"ssh upload cluster file failed: {e}")
                try:
                    self._aws_services.handle_ssh_eks_action(
                        eks_action=EKSActions.create.name
                    )
                except Exception as e:
                    raise Exception("Create eks failed")

                return

    def handle_system_check(self, event):
        logging.info("Check cloud resources")
        # check keypair
        try:
            self._aws_services.handle_aws_actions(action=AWSActions.create_keypair.name)
        except Exception as e:
            raise Exception(f"check keypair error:{e}")
        # check ec2 status
        try:
            self._aws_services.wake_up_ec2()
        except Exception as e:
            raise Exception(f"Wakeup ec2 failed :{e}")
        # check eks cluster exist
        logging.info("Check if eks cluster exist")
        try:
            cluster_name = self._aws_services.get_cluster_name()
            is_cluster_exist = self._aws_services.check_eks_exist()
            if is_cluster_exist is False:
                raise Exception(
                    f"Cluster {cluster_name} does not exist. Please clean up resouces and create a new!!"
                )
            else:
                logging.info(f"Cluster {cluster_name} exist. Continue to process... ")

        except Exception as e:
            raise Exception(f"search eks cluster failed :{e}")

        if self._action == MenuActions.resume_from_existing.name:
            # upload temp project folder
            self._aws_services.ssh_upload_selected_project_folder_from_temp()

    # Process state
    def handle_process(self, event):
        logging.info("handle_process")

        if self._platform == Platform.AWS.name:
            logging.info("Run process on AWS")

            if (
                self._action == MenuActions.run_in_local_machine.name
                or self._action == MenuActions.cleanup_cloud_resources.name
            ):
                raise Exception(
                    f"Aciton {self._action} should not enter this state. Check your code"
                )

            is_ssh = self._input_answers["is_ssh"]
            if is_ssh is False:
                process_first_n_files = self._input_answers["process_first_n_files"]
                cluster_name = self._eks_config_dict["metadata"]["name"]
                num_of_nodes = self._input_answers["num_of_nodes"]
                run_files_command = generate_run_command_from_inputs(
                    platform=self._platform,
                    process_first_n_files=process_first_n_files,
                    project_name=self._project_name,
                    num_of_nodes=num_of_nodes,
                    cluster_name=cluster_name,
                )
                # execute run file command
                self._aws_services.run_ssh_command(ssh_command=run_files_command)
            else:
                logging.info("SSH Debug mode")
                self._aws_services.run_ssh_debug_mode()
        return

    def handle_local_processing(self, event):

        logging.info("Run command in local machine")
        first_n_file = self._input_answers["process_first_n_files"]

        gismoclouddeploy(
            number=first_n_file,
            project=self._project_name,
            aws_access_key=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_region=self.aws_region,
        )
        logging.info("Copy results to origin path")
        return

    # End state
    def handle_cleanup_cloud_resources(self, event):
        logging.info("start end state")
        if self._platform == Platform.LOCAL.name:
            return
        # step 1, is clean up cloud resources
        is_cleanup_resources_after_completion = False
        if self._input_answers is not None:
            if "cleanup_resources_after_completion" in self._input_answers:
                is_cleanup_resources_after_completion = self._input_answers[
                    "cleanup_resources_after_completion"
                ]

        if self._platform == Platform.AWS.name:
            if (
                self._action == MenuActions.cleanup_cloud_resources.name
                or is_cleanup_resources_after_completion is True
            ):
                logging.info("Clean up cloud resources")
                # check if eks exist

                # delete eks cluster
                try:
                    cluster_name = self._aws_services.get_cluster_name()
                    if cluster_name is not None:
                        is_eks_cluster_exist = self._aws_services.check_eks_exist()
                        if is_eks_cluster_exist:
                            self._aws_services.handle_ssh_eks_action(
                                eks_action=EKSActions.delete.name,
                            )
                        else:
                            logging.warning(
                                f"No eks cluster {cluster_name} found, skip deleting eks cluster..!!"
                            )
                    else:
                        logging.warning(
                            f"No eks created history, skip deleting eks clsuter..!!"
                        )
                except Exception as e:
                    raise Exception(e)

                # terminate ec2
                try:

                    self._aws_services.handle_ec2_action(
                        action=EC2Actions.terminate.name,
                    )
                except Exception as e:
                    raise Exception(f"Terminate ec2 failed {e}")
                # delete key pair
                try:
                    self._aws_services.handle_aws_actions(
                        action=AWSActions.delete_keypair.name
                    )
                except Exception as e:
                    raise Exception(f"Delete keypair failed :{e}")
                # delete security group wait
                logging.warning("Delete security group not implement")

                # Delete config

                try:
                    history_path = self.saved_config_path_base + f"/{self._system_id}"
                    delete_project_folder(project_path=history_path)
                except Exception as e:
                    raise Exception(f"Delete {history_path} failed")
            else:
                try:
                    logging.info("Stop ec2")
                    self._aws_services.handle_ec2_action(
                        action=EC2Actions.stop.name,
                    )
                    logging.info("Stop ec2 success")
                except Exception as e:
                    raise Exception(f"Stop ec2 failed:{e}")
        logging.info("End of stop or clean cloud resources")

        return

    def handle_completion(self, event):
        logging.info("handle remove temp project path")
        temp_project_absoult_path = get_absolute_paht_from_project_name(
            project_name=self._project_name, base_path=self._base_path
        )
        delete_project_folder(project_path=temp_project_absoult_path)
        end_time = float(time.time())
        total_process_time = int(end_time - float(self._start_time))
        complete_array = [
            ["Applications", "Completion"],
            ["Project name", self._project_name],
            ["Total process time", total_process_time, "sec"],
            ["Action", self._action],
        ]
        table = AsciiTable(complete_array)
        print(table.table)
        return

    # ==============
    # end states methods
    # ==============

    def set_project_name(self):
        project_name = generate_project_name_from_project_path(
            project_path=self._origin_project_path
        )
        self._project_name = project_name

    def copy_origin_project_into_temp_folder(self):

        if self._project_name is None:
            raise ValueError(
                "Project name is None, Set projec name before you execute this function"
            )

        temp_project_absoult_path = get_absolute_paht_from_project_name(
            project_name=self._project_name, base_path=self._base_path
        )
        try:
            # if tem project temp does not exist create temp project
            if not os.path.exists(temp_project_absoult_path):
                logging.info(f"Create {temp_project_absoult_path}")
                os.makedirs(temp_project_absoult_path)
            # 3.8+ only!
            shutil.copytree(
                self._origin_project_path, temp_project_absoult_path, dirs_exist_ok=True
            )
            logging.info(
                f"Copy {self._origin_project_path} to {temp_project_absoult_path} success"
            )
        except Exception as e:
            raise Exception(
                f"Copy {self._origin_project_path} to {temp_project_absoult_path} failed: {e}"
            )
        return

    def handle_verify_project_folder(self):
        """
        Verify entrypoint.py
        Verify Dockerfile
        Verify requirements.txt
        Verify config.yaml
        Verify solver is defined
        """

        files_check_list = [
            "entrypoint.py",
            "Dockerfile",
            "requirements.txt",
            "config.yaml",
        ]
        temp_project_absoult_path = get_absolute_paht_from_project_name(
            project_name=self._project_name, base_path=self._base_path
        )
        for file in files_check_list:

            full_path_file = temp_project_absoult_path + "/" + file
            if not exists(full_path_file):
                raise Exception(f"{full_path_file} does not exist!!")
            logging.info(f"{file} exists !!")

        logging.info("Verify files list success")
        config_yaml = temp_project_absoult_path + "/config.yaml"
        try:
            self._config_yaml_dcit = convert_yaml_to_json(yaml_file=config_yaml)
        except Exception as e:
            raise Exception(f"convert config yaml failed")
        try:
            verify_keys_in_configfile(config_dict=self._config_yaml_dcit)
        except Exception as e:
            raise Exception(f"Verify keys in configfile error:{e}")
        solver_lic_file_local_source = self._config_yaml_dcit[
            "solver_lic_file_local_source"
        ]
        # verify solver file exists
        if solver_lic_file_local_source is None:
            logging.warning("Process without solver file")
        elif len(solver_lic_file_local_source) == 0:
            logging.warning("Process without solver file")
        else:
            logging.info("Check solver file")
            solver_absolute_path_file = (
                temp_project_absoult_path + f"/{solver_lic_file_local_source}"
            )
            if not exists(solver_absolute_path_file):
                raise Exception(f" solver {solver_absolute_path_file} does not exist")
            logging.info(f"solver file :{solver_lic_file_local_source} exist")

        return
