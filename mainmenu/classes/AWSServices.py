from os.path import exists
import os
import logging
from mainmenu.classes.constants.EC2Actions import EC2Actions
from .utilities.verification import (
    verify_keys_in_ec2_configfile,
    verify_keys_in_eks_configfile,
)
from .utilities.handle_inputs import (
    select_is_breaking_ssh,
    handle_input_ssh_custom_command,
)
import time
from .utilities.helper import get_pem_file_full_path_name
from .constants.InputDescriptions import InputDescriptions
from .utilities.convert_yaml import write_aws_setting_to_yaml
from .utilities.aws_utitlties import (
    connect_aws_client,
    connect_aws_resource,
    get_security_group_id_with_name,
    check_keypair_exist,
    get_default_vpc_id,
    get_ec2_instance_id_and_keypair_with_tags,
    get_ec2_state_from_id,
    delete_security_group,
    delete_key_pair,
    create_security_group,
    create_key_pair,
    create_instance,
    run_command_in_ec2_ssh,
    check_if_ec2_ready_for_ssh,
    get_public_ip,
    ssh_upload_folder_to_ec2,
    upload_file_to_ec2,
    get_public_ip_and_update_sshconfig,
    check_eks_cluster_with_name_exist,
)

from .constants.AWSActions import AWSActions
from .constants.EC2Status import EC2Status
from .constants.EKSActions import EKSActions


class AWSServices(object):
    """Class of controlling AWS services based on boto3"""

    def __init__(
        self,
        local_pem_path: str = None,
        local_temp_project_path=None,
        project_name: str = None,
        origin_project_path: str = None,
        system_id: str = None,
        aws_access_key: str = None,
        aws_secret_access_key: str = None,
        aws_region: str = None,
        ec2_config_dict: str = None,
        eks_config_dict: str = None,
    ) -> None:

        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.system_id = system_id
        self.origin_project_path = origin_project_path
        self.project_name = project_name
        self.local_temp_project_path = local_temp_project_path
        self.local_pem_path = local_pem_path

        self.ec2_config_dict = ec2_config_dict
        self.eks_config_dict = eks_config_dict

        # ec2 variable
        self._ec2_tags = None
        self._keypair_name = None
        self._ec2_instance_id = None
        self._ec2_image_id = None
        self._ec2_instance_type = None
        self._ec2_volume = None
        self._login_user = None
        self._securitygroup_name = None
        self._default_vpc_id = None
        self._ec2_public_ip = None
        # eks
        self._cluster_name = None
        self._nodegroup_name = None

        # private variables
        self._ssh_total_wait_time = 90
        self._ssh_wait_time_interval = 3
        self._aws_action = None

        self._ec2_client = connect_aws_client(
            client_name="ec2",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        self._ec2_resource = connect_aws_resource(
            resource_name="ec2",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        try:
            self.impor_ec2_parameters_from_dict()
        except Exception as e:
            raise Exception(f"Import ec2 parameter failed: {e}")
        try:
            self.impor_eks_parameters_from_dict()
        except Exception as e:
            raise Exception(f"Import ec2 parameter failed: {e}")

    def get_cluster_name(self):
        return self._cluster_name

    def get_security_group_ids(self):
        return self._securitygroup_ids

    def impor_ec2_parameters_from_dict(self):
        ec2_config_dict = self.ec2_config_dict
        if self.ec2_config_dict is None:
            raise Exception(f"{self.ec2_config_dict} is None")
        verify_keys_in_ec2_configfile(config_dict=ec2_config_dict)
        self._ec2_tags = ec2_config_dict["tags"]
        self._keypair_name = ec2_config_dict["key_pair_name"]
        self._ec2_instance_id = ec2_config_dict["ec2_instance_id"]
        self._ec2_image_id = ec2_config_dict["ec2_image_id"]
        self._ec2_instance_type = ec2_config_dict["ec2_instance_type"]
        self._ec2_volume = ec2_config_dict["ec2_volume"]
        self._login_user = ec2_config_dict["login_user"]
        self._securitygroup_name = ec2_config_dict["securitygroup_name"]
        logging.info("Import EC2 parameters success")
        self._pem_file = get_pem_file_full_path_name(
            self.local_pem_path, self._keypair_name
        )

        return

    def impor_eks_parameters_from_dict(self):
        eks_config_dict = self.eks_config_dict

        if eks_config_dict is None:
            raise Exception(f"eks_config_dict is None")
        verify_keys_in_eks_configfile(config_dict=eks_config_dict)
        self._cluster_name = eks_config_dict["metadata"]["name"]
        self._nodegroup_name = eks_config_dict["nodeGroups"][0]["name"]
        logging.info("Import EKS parameters success")
        return

    def create_ec2_from_template_file(self):
        # step 1 , check keypair

        self.handle_aws_actions(action=AWSActions.create_keypair.name)
        # step 2 . get default vpc id to create security group
        self.handle_aws_actions(action=AWSActions.get_default_vpc_id.name)
        # step 3 . chcek security group
        self.handle_aws_actions(action=AWSActions.create_securitygroup.name)
        securitygroup_ids = self.get_security_group_ids()
        ec2_info = get_ec2_instance_id_and_keypair_with_tags(
            ec2_client=self._ec2_client, tag_key_f="Name", tag_val_f=self.system_id
        )

        if ec2_info is not None:
            InstanceId = ec2_info["InstanceId"]
            KeyName = ec2_info["KeyName"]
            status = ec2_info["State"]["Name"]
            if status != EC2Status.terminated.name:
                logging.error(
                    f"EC2 {InstanceId} with name:{KeyName} exists, and i's not at terminated state. current status: {status}"
                )
                logging.error(
                    f"This application limits creating one ec2 instance per account. If you are running this application in multiple computers. \n You need to wait it finished. Or you can login into you AWS console and create the AWS resouces manully."
                )
                raise Exception("Create ec2 failed. Duplicate ec2 instances exist")
            else:
                logging.warning(
                    f"EC2 {InstanceId} with name:{KeyName} found. It's terminated"
                )

        self.handle_aws_actions(action=AWSActions.create_ec2_instance.name)
        return

    def handle_aws_actions(self, action: AWSActions):

        if action == AWSActions.create_securitygroup.name:
            logging.info("Create security group action")
            if self._default_vpc_id is None:
                raise Exception("default vpc id is None")

            sg_id = get_security_group_id_with_name(
                ec2_client=self._ec2_client, group_name=self._securitygroup_name
            )
            if sg_id is None:
                security_info_dict = create_security_group(
                    ec2_client=self._ec2_client,
                    vpc_id=self._default_vpc_id,
                    tags=self._ec2_tags,
                    group_name=self._securitygroup_name,
                )
                self._securitygroup_ids = [security_info_dict["security_group_id"]]
                logging.info(
                    f"Create SecurityGroupIds : {self._securitygroup_ids} in vpc_id:{self._default_vpc_id} success"
                )
            else:
                self._securitygroup_ids = [sg_id]
                logging.info(
                    f"Found security groupd with name: {self._securitygroup_name}  ids: {self._securitygroup_ids}"
                )
                self._securitygroup_ids = [sg_id]
        elif action == AWSActions.delete_securitygroup.name:
            logging.info("Delete security group action")
            sg_id = get_security_group_id_with_name(
                ec2_client=self._ec2_client, group_name=self._securitygroup_name
            )
            if sg_id is None:
                logging.info(
                    f"No security group name :{self._securitygroup_name} found"
                )
            else:
                logging.info(
                    f"Found security groupd with name: {self._securitygroup_name}  id: {sg_id}"
                )
                self._securitygroup_ids = [sg_id]
                logging.info(f"Deleting {self._securitygroup_ids}")
                delete_security_group(ec2_client=self._ec2_client, group_id=sg_id)

        elif action == AWSActions.create_keypair.name:
            try:
                logging.info("Create keypair action")
                if self._keypair_name is None:
                    raise ValueError("Key pair name is None")
                if not check_keypair_exist(
                    ec2_client=self._ec2_client, keypair_anme=self._keypair_name
                ):

                    logging.info(
                        f"keypair:{self._keypair_name} does not exist create a new keypair in {self.local_pem_path}"
                    )
                    create_key_pair(
                        ec2_client=self._ec2_client,
                        keyname=self._keypair_name,
                        file_location=self.local_pem_path,
                    )
                    logging.info("=============================")
                    logging.info(f"pem_file :{self._keypair_name}")
                    logging.info(f"self.local_pem_path :{self.local_pem_path}")
                    logging.info("=============================")

                else:
                    logging.info(f"keypair:{self._keypair_name} exist")

                    if not exists(self._pem_file):
                        logging.warning(
                            f"Find key pair on AWS but local {self._pem_file} is missiong"
                        )
                        logging.warning(
                            "You can use clean resource to delete keypari and regenerate a new one"
                        )
                        raise Exception(
                            "Please clean previous resources and run menu again !!"
                        )
                    logging.info("=============================")
                    logging.info(f"self._pem_file :{self._pem_file}")
                    logging.info("=============================")
            except Exception as e:
                raise Exception(f"Create keypair fialed:{e}")

        elif action == AWSActions.delete_keypair.name:
            logging.info("Delete keypair action")
            if not check_keypair_exist(
                ec2_client=self._ec2_client, keypair_anme=self._keypair_name
            ):
                logging.info(f"keypair:{self._keypair_name} does not exist do nothing ")
            else:
                logging.info(f"Deleting:{self._keypair_name} ")
                delete_key_pair(
                    ec2_client=self._ec2_client, key_name=self._keypair_name
                )
                if exists(self._pem_file):
                    os.remove(self._pem_file)
                    logging.info(f"Delete local pem: {self._pem_file} success")
        elif action == AWSActions.get_default_vpc_id.name:
            self._default_vpc_id = get_default_vpc_id(ec2_client=self._ec2_client)
            logging.info(f"get and set default vpc id :{self._default_vpc_id} ")

        elif action == AWSActions.create_ec2_instance.name:
            logging.info("Create ec2 action !!!")
            try:
                if self._securitygroup_ids is None or not len(self._securitygroup_ids):
                    raise Exception("securitygroup_ids is None")
                if self._keypair_name is None:
                    raise Exception("key_pair_name is None")

                ec2_instance_id = create_instance(
                    ImageId=self._ec2_image_id,
                    InstanceType=self._ec2_instance_type,
                    key_piar_name=self._keypair_name,
                    ec2_client=self._ec2_client,
                    tags=self._ec2_tags,
                    SecurityGroupIds=self._securitygroup_ids,
                    volume=self._ec2_volume,
                )
                logging.info(f"ec2_instance_id: {ec2_instance_id}")
                self._ec2_instance_id = ec2_instance_id
                logging.info("-------------------")
                logging.info(f"Create ec2 bastion completed:{self._ec2_instance_id}")
                logging.info("-------------------")
                get_public_ip_and_update_sshconfig(
                    ec2_client=self._ec2_client,
                    ec2_instance_id=self._ec2_instance_id,
                    system_id=self.system_id,
                    login_user=self._login_user,
                    keypair_name=self._keypair_name,
                    local_pem_path=self.local_pem_path,
                )

            except Exception as e:
                raise Exception(f"Create ec2 instance failed: \n {e}")

        elif action == AWSActions.check_ec2_exist.name:
            logging.info("Check ec2 exist !!!")

    def export_ec2_params_to_file(self, export_file):
        self._export_ec2_config_file = export_file
        # check path exist
        path, file = os.path.split(export_file)
        if not os.path.exists(path):
            os.mkdir(path)

        if self._ec2_instance_id is None:
            raise Exception("export ec2 failed : instance id is None")

        config_dict = {}
        config_dict["securitygroup_name"] = self._securitygroup_name
        config_dict["ec2_image_id"] = self._ec2_image_id
        config_dict["ec2_instance_id"] = self._ec2_instance_id
        config_dict["ec2_instance_type"] = self._ec2_instance_type
        config_dict["ec2_volume"] = self._ec2_volume
        config_dict["key_pair_name"] = self._keypair_name
        config_dict["login_user"] = self._login_user
        config_dict["tags"] = self._ec2_tags

        write_aws_setting_to_yaml(file=export_file, setting=config_dict)

        logging.info("Export eks config")
        return

    def hanle_ec2_setup_dependencies(self):
        logging.info("Start setup gcd environments on AWS ec2")

        instance = check_if_ec2_ready_for_ssh(
            instance_id=self._ec2_instance_id,
            wait_time=self._ssh_total_wait_time,
            delay=self._ssh_wait_time_interval,
            pem_location=self._pem_file,
            user_name=self._login_user,
            ec2_resource=self._ec2_resource,
        )

        logging.info(f"instance ready :{instance}")

        self._ec2_public_ip = get_public_ip(
            ec2_client=self._ec2_client, instance_id=self._ec2_instance_id
        )
        logging.info("---------------------")
        logging.info(f"public_ip :{self._ec2_public_ip}")
        logging.info("---------------------")

        logging.info("-------------------")
        logging.info(f"upload install.sh")
        logging.info("-------------------")
        # upload .env
        local_env = "./deploy/install.sh"
        remote_env = f"/home/{self._login_user}/install.sh"
        upload_file_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_file,
            local_file=local_env,
            remote_file=remote_env,
            ec2_resource=self._ec2_resource,
        )
        # run install.sh
        logging.info("=============================")
        logging.info("Run install.sh ")
        logging.info("=============================")
        command = f"bash /home/{self._login_user}/install.sh"
        run_command_in_ec2_ssh(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            command=command,
            pem_location=self._pem_file,
            ec2_resource=self._ec2_resource,
        )

        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy"
        # upload .env
        logging.info("-------------------")
        logging.info(f"upload .env")
        logging.info("-------------------")
        # upload .env
        local_env = ".env"

        remote_env = f"{remote_base_path}/.env"
        upload_file_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_file,
            local_file=local_env,
            remote_file=remote_env,
            ec2_resource=self._ec2_resource,
        )

        logging.info("-------------------")
        logging.info(f"Set up aws cli credentials ")
        logging.info("-------------------")
        ssh_command = f"aws configure set aws_access_key_id {self.aws_access_key} \n aws configure set aws_secret_access_key {self.aws_secret_access_key} \n aws configure set default.region {self.aws_region}"
        run_command_in_ec2_ssh(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_file,
            ec2_resource=self._ec2_resource,
            command=ssh_command,
        )

        remote_projects_folder = f"{remote_base_path}/{self.project_name}"
        # remote_temp_folder = f"{remote_base_path}/temp"
        logging.info("-------------------")
        logging.info(f"upload local project folder to ec2 projects")
        logging.info(f"local folder:{self.local_temp_project_path}")
        logging.info(f"remote folder:{remote_projects_folder}")
        logging.info("-------------------")

        ssh_upload_folder_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_file,
            local_project_path_base=self.local_temp_project_path,
            remote_project_path_base=remote_projects_folder,
            ec2_resource=self._ec2_resource,
        )
        logging.info("Setup ec2 success!!")
        return

    def generate_eks_config_and_export(
        self, eks_config_yaml_dcit: str, export_file: str
    ):
        logging.info("import from tempaltes and change eks variables")

        self._cluster_name = eks_config_yaml_dcit["metadata"]["name"]
        logging.info(f"cluster name:{self._cluster_name }")
        # export file
        verify_keys_in_eks_configfile(config_dict=eks_config_yaml_dcit)
        write_aws_setting_to_yaml(file=export_file, setting=eks_config_yaml_dcit)

        logging.info("Export eks config success")
        return

    def ssh_update_eks_cluster_file(self, src_file: str):
        # ec2_name = self.get_ec2_name_from_tags()
        remote_cluster = f"/home/{self._login_user}/gismo-cloud-deploy/created_resources_history/{self.system_id}/cluster.yaml"

        upload_file_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_file,
            local_file=src_file,
            remote_file=remote_cluster,
            ec2_resource=self._ec2_resource,
        )

    def handle_ssh_eks_action(
        self,
        eks_action: str,
    ):

        ssh_command_list = {}
        instance_id = self._ec2_instance_id
        cluster_name = self._cluster_name
        nodegroup_name = self._nodegroup_name
        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy"
        remote_cluster_file = f"{remote_base_path}/created_resources_history/{self.system_id}/cluster.yaml"
        login_user = self._login_user

        logging.info("=============================")
        logging.info(f"self._self._pem_file :{self._pem_file}")
        logging.info(f"cluster_name :{cluster_name}")
        logging.info("=============================")

        if instance_id is None:
            raise Exception("instance id is None")

        if cluster_name is None or nodegroup_name is None:
            raise Exception(f"cluster_name {cluster_name} or f{nodegroup_name} is None")

        if eks_action == EKSActions.create.name:

            logging.info("SSH create eks")
            command = f"eksctl create cluster -f {remote_cluster_file}"
            ssh_command_list["Create EKS cluster"] = command

        elif eks_action == EKSActions.delete.name:
            logging.info("set delete eks culster command ")
            # scale down if cluster exist
            scaledown_command = f'rec="$(eksctl get cluster | grep {cluster_name})" \n if [ -n "$rec" ] ; then eksctl scale nodegroup --cluster {cluster_name} --name {nodegroup_name} --nodes 0; fi'
            ssh_command_list["scaledonw cluster"] = scaledown_command
            # delete cluster if cluster exist
            delete_eks_command = f'rec="$(eksctl get cluster | grep {cluster_name})" \n if [ -n "$rec" ] ; then eksctl delete cluster -f {remote_cluster_file}; fi'

            ssh_command_list["Delete EKS cluster"] = delete_eks_command

        elif eks_action == EKSActions.list.name:
            logging.info("Run list eks")
            command = f"eksctl get cluster"
            ssh_command_list["List EKS cluster"] = command

        elif eks_action == EKSActions.check_cluster_exist.name:
            logging.info("chekc cluster exist")

        elif eks_action == EKSActions.scaledownzero.name:
            logging.info("SSH scale down zero eks")
            command = f'rec="$(eksctl get cluster | grep {cluster_name})" \n if [ -n "$rec" ] ; then eksctl scale nodegroup --cluster {cluster_name} --name {nodegroup_name} --nodes 0; fi'
            ssh_command_list["Scale down eks"] = command

        for description, command in ssh_command_list.items():
            logging.info(description)
            logging.info(command)
            try:
                run_command_in_ec2_ssh(
                    user_name=login_user,
                    instance_id=instance_id,
                    command=command,
                    pem_location=self._pem_file,
                    ec2_resource=self._ec2_resource,
                )
            except Exception as e:
                raise Exception(f"run eks command {description} file failed \n {e}")

    def wake_up_ec2(self, wait_time: int = 90, delay: int = 5):

        logging.info("Wake up ec2")
        ec2_instance_id = self._ec2_instance_id

        if ec2_instance_id is None:
            raise Exception(
                "ec2 instance id is None, Import from exsiting file or create a new one"
            )
        is_ec2_state_ready = False
        while wait_time > 0 or not is_ec2_state_ready:
            wait_time -= delay
            ec2_state = get_ec2_state_from_id(
                ec2_client=self._ec2_client, id=ec2_instance_id
            )
            logging.info(f"ec2_state :{ec2_state} waitng:{wait_time}")
            if (
                ec2_state == EC2Status.stopped.name
                or ec2_state == EC2Status.running.name
            ):
                logging.info(f"In stopped or running running sate")
                is_ec2_state_ready = True
                break
            time.sleep(delay)

        if is_ec2_state_ready is False:
            raise ValueError(f"Wait ec2 state overtime :{ec2_state}")

        if ec2_state == EC2Status.stopped.name:
            logging.info("EC2 in stop state, wake up ec2")
            # self.set_ec2_action(action=EC2Action.start.name)
            self.handle_ec2_action(action=EC2Actions.start.name)

        if ec2_state == EC2Status.running.name:
            logging.info("EC2 in running state")
            self._ec2_public_ip = get_public_ip(
                ec2_client=self._ec2_client, instance_id=ec2_instance_id
            )
            logging.info("Update ssh config")
            get_public_ip_and_update_sshconfig(
                ec2_client=self._ec2_client,
                ec2_instance_id=self._ec2_instance_id,
                system_id=self.system_id,
                login_user=self._login_user,
                keypair_name=self._keypair_name,
                local_pem_path=self.local_pem_path,
            )
            # add_public_ip_to_sshconfig(
            #     public_ip=self._ec2_public_ip,
            #     login_user=self._login_user,
            #     key_pair_name=self._keypair_name
            # )

        return

    def check_eks_exist(
        self,
    ) -> bool:
        eks_client = connect_aws_client(
            client_name="eks",
            key_id=self.aws_access_key,
            secret=self.aws_secret_access_key,
            region=self.aws_region,
        )
        try:
            is_cluster_exist = check_eks_cluster_with_name_exist(
                eks_client=eks_client, cluster_name=self._cluster_name
            )
            return is_cluster_exist
        except Exception as e:
            raise Exception("check eks exist failed")

    def run_ssh_command(
        self,
        ssh_command: str,
    ):

        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy/"
        full_ssh_command = (
            f"cd {remote_base_path} \n source ./venv/bin/activate \n {ssh_command} "
        )

        run_command_in_ec2_ssh(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_file,
            ec2_resource=self._ec2_resource,
            command=full_ssh_command,
        )

    def run_ssh_debug_mode(self):
        # Run any command
        logging.info("enter debug mode")
        is_breaking = False
        while not is_breaking:
            custom_ssh_command = handle_input_ssh_custom_command()
            self.run_ssh_command(ssh_command=custom_ssh_command)
            logging.info("SSH command completed")
            is_breaking = select_is_breaking_ssh()
        logging.info("exit debug mode")

    def handle_ec2_action(
        self,
        action: str,
    ):
        if action is None:
            raise Exception("action is None")
        ec2_instance_id = self._ec2_instance_id
        login_user = self._login_user

        if login_user is None:
            raise Exception("login user is None")
        if ec2_instance_id is None:
            raise Exception("ec2 instance id is None")

        if action == EC2Actions.start.name:
            if ec2_instance_id is not None:
                res = self._ec2_resource.instances.filter(
                    InstanceIds=[ec2_instance_id]
                ).start()  # for stopping an ec2 instance
                instance = check_if_ec2_ready_for_ssh(
                    instance_id=ec2_instance_id,
                    wait_time=self._ssh_total_wait_time,
                    delay=self._ssh_wait_time_interval,
                    pem_location=self._pem_file,
                    user_name=login_user,
                    ec2_resource=self._ec2_resource,
                )
                ec2_public_ip = get_public_ip(
                    ec2_client=self._ec2_client, instance_id=ec2_instance_id
                )
                logging.info("---------------------------------")
                logging.info(f"public_ip :{ec2_public_ip}")
                logging.info("---------------------------------")
                logging.info("Ec2 start")

        elif action == EC2Actions.stop.name:
            try:
                res = self._ec2_resource.instances.filter(
                    InstanceIds=[ec2_instance_id]
                ).stop()  # for stopping an ec2 instance
            except Exception as e:
                raise Exception(f"Stop ec2 failed:{e}")
        elif action == EC2Actions.terminate.name:
            logging.info("Get ec2 terminate")
            try:
                res_term = self._ec2_resource.instances.filter(
                    InstanceIds=[ec2_instance_id]
                ).terminate()  # for terminate an ec2 insta
            except Exception as e:
                raise Exception(f"Terminate ec2 failed:{e}")
        return

    def ssh_upload_selected_project_folder_from_temp(self):

        remote_base_path = f"/home/{self._login_user}/gismo-cloud-deploy"
        remote_projects_folder = f"{remote_base_path}/{self.project_name}"
        logging.info("-------------------")
        logging.info(f"upload local project folder to ec2 projects")
        logging.info(f"local folder:{self.local_temp_project_path}")
        logging.info(f"remote folder:{remote_projects_folder}")
        logging.info("-------------------")

        ssh_upload_folder_to_ec2(
            user_name=self._login_user,
            instance_id=self._ec2_instance_id,
            pem_location=self._pem_file,
            local_project_path_base=self.local_temp_project_path,
            remote_project_path_base=remote_projects_folder,
            ec2_resource=self._ec2_resource,
        )

        return
