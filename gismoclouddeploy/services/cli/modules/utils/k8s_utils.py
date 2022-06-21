import time
from kubernetes import client, config
from server.models.Configurations import Configurations
from typing import Tuple
import logging
import yaml

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def create_k8s_from_yaml(file_path: str, file_name: str, app_name: str) -> bool:
    config.load_kube_config()
    apps_v1_api = client.AppsV1Api()
    full_path_name = file_path + "/" + file_name
    try:
        with open(full_path_name) as f:
            dep = yaml.safe_load(f)
            logger.info(f" ========= Create {app_name} app_name:{app_name} ========= ")
            try:
                resp = apps_v1_api.create_namespaced_deployment(
                    body=dep, namespace="default"
                )
                print("Created. status='%s'" % str(resp.status))
                return True
            except Exception as e:
                print(f"no deplyment.yaml {file_name}")
                raise e
    except Exception as e:
        print(f"openf file {full_path_name} failed: {e}")
        raise e


def read_k8s_yml(full_path_name: str):
    config.load_kube_config()
    # full_path_name = file_path + "/" + file_name
    try:
        with open(full_path_name) as f:
            dep = yaml.safe_load(f)
            return dep
    except Exception as e:
        logger.error(f"cannot open yaml file: {e}")
        raise e


def create_k8s_svc_from_yaml(
    full_path_name: str = None, namspace: str = "default"
) -> bool:
    try:
        file_setting = read_k8s_yml(full_path_name=full_path_name)
    except Exception as e:
        raise e
    config.load_kube_config()
    apps_v1_api = client.CoreV1Api()
    try:
        resp = apps_v1_api.create_namespaced_service(
            body=file_setting, namespace=namspace
        )
        print("Created. status='%s'" % str(resp.status))
        return True
    except Exception as e:
        logger.error(f"create k8s svc error: {e}")
        raise e


def create_k8s_deployment_from_yaml(
    service_name: str = None,
    image_url_tag: str = None,
    imagePullPolicy: str = None,
    desired_replicas: int = 1,
    file_name: str = None,
    namspace: str = "default",
) -> bool:
    try:
        file_setting = read_k8s_yml(full_path_name=file_name)
    except Exception as e:
        raise e
    default_image = file_setting["spec"]["template"]["spec"]["containers"][0]["image"]
    default_replicas = file_setting["spec"]["replicas"]
    default_imagePullPolicy = file_setting["spec"]["template"]["spec"]["containers"][0][
        "imagePullPolicy"
    ]
    default_replicas = file_setting["spec"]["replicas"]

    print(str(desired_replicas), image_url_tag, imagePullPolicy)
    # update setting if not nont
    if image_url_tag is not None and image_url_tag != default_image:
        logger.info(f"update k8s image {image_url_tag}")
        file_setting["spec"]["template"]["spec"]["containers"][0][
            "image"
        ] = image_url_tag

    if desired_replicas != 1 and desired_replicas != default_replicas:
        logger.info(f"update k8s replicas {desired_replicas}")
        file_setting["spec"]["replicas"] = int(desired_replicas)

    if imagePullPolicy is not None and imagePullPolicy != default_imagePullPolicy:
        logger.info(f"update imagePullPolicy {imagePullPolicy}")
        file_setting["spec"]["template"]["spec"]["containers"][0][
            "imagePullPolicy"
        ] = imagePullPolicy

    config.load_kube_config()
    apps_v1_api = client.AppsV1Api()
    try:
        resp = apps_v1_api.create_namespaced_deployment(
            body=file_setting, namespace=namspace
        )
        print("Created. status='%s'" % str(resp.status))
        return True
    except Exception as e:
        logger.error(f"create k8s deployment error: {e}")
        raise e


def get_k8s_deployment(prefix: str = None) -> str:
    config.load_kube_config()
    v1 = client.AppsV1Api()
    resp = v1.list_namespaced_deployment(namespace="default")
    dep = []
    for i in resp.items:
        if i.metadata.name == "worker":
            dep.append(i)

    print(dep[0])


def get_k8s_pod_info(prefix: str = None) -> dict:
    config.load_kube_config()
    v1 = client.AppsV1Api()
    resp = v1.list_replica_set_for_all_namespaces(watch=False)
    pods = []

    # find the latest version of deployemnt
    max_version = 0
    pod_name = None
    available_replicas = 0
    for i in resp.items:
        pod_prefix = i.metadata.name.split("-")[0]
        if pod_prefix == prefix:
            if (
                int(i.metadata.annotations["deployment.kubernetes.io/revision"])
                > max_version
            ):
                max_version = int(
                    i.metadata.annotations["deployment.kubernetes.io/revision"]
                )
                pod_name = i.metadata.name
                available_replicas = i.status.available_replicas

    return {
        "pod_name": pod_name,
        "max_version": max_version,
        "available_replicas": available_replicas,
    }


def get_k8s_image_and_tag_from_deployment(prefix: str = None) -> Tuple[str, str, str]:
    try:
        config.load_kube_config()
        v1 = client.AppsV1Api()
        resp = v1.list_namespaced_deployment(namespace="default")
        deployment = []
        for i in resp.items:
            if i.metadata.name == prefix:
                deployment.append(i)
        if len(deployment) > 0:
            for po in deployment:
                full_image_url = po.spec.template.spec.containers[0].image
                logger.info(f"=========> {full_image_url}")
                image, image_tag = full_image_url.split(":")
                status = po.status
                return image, image_tag, status

        return None, None, None
    except Exception as e:
        raise e


def check_k8s_services_exists(name: str = None) -> bool:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    resp = v1.list_service_for_all_namespaces(watch=False)
    for i in resp.items:
        if i.metadata.name == name:
            return True
    return False


def get_k8s_pod_name(pod_name: str = None) -> str:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        podname = i.metadata.name.split("-")[0]
        if podname == pod_name:
            return i.metadata.name

    return None
