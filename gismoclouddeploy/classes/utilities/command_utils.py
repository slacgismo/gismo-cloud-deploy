from re import I
import botocore
import time
from .k8s_utils import (
    get_k8s_image_and_tag_from_deployment,
    create_k8s_deployment_from_yaml,
)

from .invoke_function import invoke_kubectl_delete_deployment

import logging


def create_or_update_k8s_deployment(
    service_name: str = None,
    image_base_url: str = None,
    image_tag: str = None,
    imagePullPolicy: str = "Always",
    desired_replicas: int = 1,
    k8s_file_name: str = None,
    # rollout: bool = False,
    namespace: str = "default",
):

    try:
        curr_image, curr_tag, curr_status = get_k8s_image_and_tag_from_deployment(
            prefix=service_name, namespace=namespace
        )
        # print(curr_image,curr_tag, curr_status )
        image_url = f"{image_base_url}:{image_tag}"
        if curr_status is None:
            # Deployment does not exist

            logging.info(f"Deployment {image_url} does not exist ")
            logging.info(f" Create {image_url} deployment  namespace: {namespace}")
            create_k8s_deployment_from_yaml(
                service_name=service_name,
                image_url_tag=image_url,
                imagePullPolicy=imagePullPolicy,
                desired_replicas=desired_replicas,
                file_name=k8s_file_name,
                namspace=namespace,
            )
        else:
            logging.info(f"Deployment {service_name}:{curr_tag} exist")

            if (
                curr_status.unavailable_replicas is not None
                or curr_tag != image_tag
                or int(curr_status.replicas) != int(desired_replicas)
            ):

                if curr_status.unavailable_replicas is not None:
                    logging.info("Deployment status error")
                if int(curr_status.replicas) != int(desired_replicas):
                    logging.info(
                        f"Update replicas from:{curr_status.replicas} to {desired_replicas}"
                    )
                if curr_tag != image_tag:
                    logging.info(
                        f"Update from {service_name}:{curr_tag} to {service_name}:{image_tag}"
                    )

                logging.info(f"Delete  {service_name}:{curr_tag} ")
                output = invoke_kubectl_delete_deployment(name=service_name)
                # logger.info(output)

                # re-create deplpoyment

                create_k8s_deployment_from_yaml(
                    service_name=service_name,
                    image_url_tag=image_url,
                    imagePullPolicy=imagePullPolicy,
                    desired_replicas=desired_replicas,
                    file_name=k8s_file_name,
                )
    except Exception as e:
        logging.info(e)
        raise e


def verify_keys_in_configfile(config_dict: dict):
    try:
        verify_a_key_in_dict(dict_format=config_dict, key="scale_eks_nodes_wait_time")
        verify_a_key_in_dict(dict_format=config_dict, key="interval_of_wait_pod_ready")
        verify_a_key_in_dict(dict_format=config_dict, key="data_bucket")
        verify_a_key_in_dict(dict_format=config_dict, key="file_pattern")
        verify_a_key_in_dict(dict_format=config_dict, key="process_column_keywords")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_bucket")
        verify_a_key_in_dict(dict_format=config_dict, key="saved_path_cloud")
        verify_a_key_in_dict(dict_format=config_dict, key="acccepted_idle_time")
        verify_a_key_in_dict(dict_format=config_dict, key="interval_of_checking_sqs")
        verify_a_key_in_dict(dict_format=config_dict, key="filename")
        verify_a_key_in_dict(dict_format=config_dict, key="repeat_number_per_round")
        verify_a_key_in_dict(dict_format=config_dict, key="is_celeryflower_on")
        # Solver
        verify_a_key_in_dict(dict_format=config_dict, key="solver_name")
        verify_a_key_in_dict(
            dict_format=config_dict, key="solver_lic_target_path_in_images_dest"
        )
        verify_a_key_in_dict(
            dict_format=config_dict, key="solver_lic_file_local_source"
        )
        logging.info("Verify config key success")
    except Exception as e:
        raise Exception(f"Assert error {e}")


def verify_a_key_in_dict(dict_format: dict, key: str) -> None:
    try:
        assert key in dict_format
    except Exception:
        raise Exception(f"does not contain {key}")


def do_nothing_and_wait(wait_time: int = 60, delay: int = 3):

    while wait_time > 0:
        time.sleep(delay)
        wait_time -= delay
        logging.info(f"Waiting.. {wait_time} sec")
    return
