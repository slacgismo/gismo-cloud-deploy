import re
import time
import logging
from kubernetes import client, config
from utils.aws_utils import check_environment_is_aws

from models.Config import Config
import logging
from typing import List
import yaml

from halo import Halo
from models.Config import Config
from utils.invoke_function import (
    invoke_kubectl_apply,
    invoke_eksctl_scale_node,
    get_k8s_pod_name,
)

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def num_container_ready(container_prefix: str) -> int:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    num_container_running = 0
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        podname = i.metadata.name.split("-")[0]
        if podname == container_prefix:
            logger.info(f"{i.metadata.name}: {i.status.container_statuses[-1].state}")
            if i.status.container_statuses[-1].ready:
                num_container_running += 1
    return num_container_running


def wait_container_ready(
    num_container: str, container_prefix: str, counter: int, delay: int
) -> bool:
    cunrrent_num_container = 0
    print(counter)
    while counter:
        cunrrent_num_container = num_container_ready(container_prefix=container_prefix)
        if cunrrent_num_container == num_container:
            logger.info(f"{num_container} pods are running")
            return True
        counter -= delay
        logger.info(
            f"waiting ....counter: {counter - delay} Time: {time.ctime(time.time())}"
        )
        time.sleep(delay)

    return False


def scale_nodes_and_wait(
    scale_node_num: int, counter: int, delay: int, config_params_obj: Config
) -> bool:

    num_nodes = num_of_nodes_ready()
    print(f"scale node {scale_node_num}, current node number: {num_nodes}")
    if num_nodes == scale_node_num:
        logger.info(f"{num_nodes} nodes is ready ")
        return True
    # num_node is not equal ,
    logger.info(f"scale node num: {scale_node_num}")
    scale_node_number(
        min_nodes=scale_node_num,
        cluster_name=config_params_obj.cluster_name,
        nodegroup_name=config_params_obj.nodegroup_name,
    )

    while counter:
        num_nodes = num_of_nodes_ready()
        print(
            f"waiting {scale_node_num} ready , current num_nodes:{num_nodes}  ....counter: {counter} Time: {time.ctime(time.time())}"
        )
        if num_nodes == scale_node_num:
            return True
        counter -= delay
        time.sleep(delay)
    return False


def num_of_nodes_ready():
    # print("check node status")
    config.load_kube_config()
    v1 = client.CoreV1Api()
    response = v1.list_node()
    nodes = []
    num_of_node_ready = 0
    for node in response.items:

        # print(node.metadata.labels['kubernetes.io/hostname'])
        cluster = node.metadata.labels["alpha.eksctl.io/cluster-name"]
        nodegroup = node.metadata.labels["alpha.eksctl.io/nodegroup-name"]
        hostname = node.metadata.labels["kubernetes.io/hostname"]
        instance_type = node.metadata.labels["beta.kubernetes.io/instance-type"]
        region = node.metadata.labels["topology.kubernetes.io/region"]
        status = node.status.conditions[-1].status  # only looks the last
        status_type = node.status.conditions[-1].type  # only looks the last
        if bool(status) == True:
            num_of_node_ready += 1
    return num_of_node_ready


def scale_node_number(min_nodes: int, cluster_name: str, nodegroup_name: str):
    # check if input is integer
    # assert(type(min_nodes) is int, f"Input {min_nodes} is not an")
    # gcd-node-group-lt
    try:
        node = int(min_nodes)
    except Exception as e:
        print(f"Error: input {min_nodes} is not a integer")
        return False

    if int(min_nodes) == 0:

        res = invoke_eksctl_scale_node(
            cluster_name=cluster_name,
            group_name=nodegroup_name,
            nodes=0,
            nodes_max=1,
            nodes_min=0,
        )
        print(f"scale down to {min_nodes}, res: {res}")
    else:
        res = invoke_eksctl_scale_node(
            cluster_name=cluster_name,
            group_name=nodegroup_name,
            nodes=min_nodes,
            nodes_max=min_nodes,
            nodes_min=min_nodes,
        )
        print(f"scale up to {min_nodes}, res:{res}")


def match_pod_ip_to_node_name(pods_name_sets: set) -> dict:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    # print("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    pods = {}
    for i in ret.items:
        # print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
        podname = i.metadata.name.split("-")[0]
        if podname in pods_name_sets:
            _pod_name = i.metadata.name
            _node_name = i.spec.node_name
            ip = i.status.pod_ip
            pods[ip] = dict(POD_NAME=_pod_name, NOD_NAME=_node_name)

    # for key, value in pods.items():
    #     print(key, value)
    return pods


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


def create_or_update_k8s(config_params_obj: Config, env: str = "local"):
    """Read worker config, if the replicas of woker is between from config.yaml and k8s/k8s-aws or k8s/k8s-local
    Update the replicas number
    """
    k8s_path = ""
    if env == "local":
        k8s_path = "./k8s/k8s-local"
    else:
        k8s_path = "./k8s/k8s-aws"

    logger.info(" ========= Check K8s is status ========= ")

    worker_pod = get_k8s_pod_name("worker")
    webapp_pod = get_k8s_pod_name("webapp")
    redis = get_k8s_pod_name("redis")
    rabbitmq = get_k8s_pod_name("rabbitmq")
    print(f"{worker_pod}, {webapp_pod},{redis}, {rabbitmq}")
    if worker_pod is None or webapp_pod is None or redis is None or rabbitmq is None:
        logger.info(
            f" ========= Worker or Webapp is none found,  apply K8s from {k8s_path} ========= "
        )
        try:
            worker_setting = read_k8s_yml(
                file_path=k8s_path, file_name="worker.deployment.yaml"
            )
        except Exception as e:
            raise e

        worker_default_replicas = worker_setting["spec"]["replicas"]
        # invoke kubectl apply -f .(folder)
        response = invoke_kubectl_apply(k8s_path)
        logger.info(response)
        # check rabbitmq
        is_rabbitmq_pod_ready = wait_container_ready(
            num_container=1, container_prefix="rabbitmq", counter=60, delay=1
        )
        if is_rabbitmq_pod_ready is False:
            logger.error("Waiting redis pod ready over time")
            raise Exception("Waiting over time")
        # check redis
        is_redis_pod_ready = wait_container_ready(
            num_container=1, container_prefix="redis", counter=60, delay=1
        )
        if is_redis_pod_ready is False:
            logger.error("Waiting redis pod ready over time")
            raise Exception("Waiting over time")
        # check webapp
        is_webapp_pod_ready = wait_container_ready(
            num_container=1, container_prefix="webapp", counter=60, delay=1
        )
        if is_webapp_pod_ready is False:
            logger.error("Waiting webapp pod ready over time")
            raise Exception("Waiting over time")
        # check worker
        is_worker_pod_ready = wait_container_ready(
            num_container=worker_default_replicas,
            container_prefix="worker",
            counter=60,
            delay=1,
        )
        if is_worker_pod_ready is False:
            logger.error("Waiting worker pod ready over time")
            raise Exception("Waiting over time")

    logger.info(" ========= Compare k8s Worker Setting with config.yaml ========= ")

    current_woker_replicas = num_container_ready(container_prefix="worker")
    try:
        replace_k8s_yaml_with_replicas(
            file_path=k8s_path,
            file_name="worker.deployment.yaml",
            new_replicas=int(config_params_obj.worker_replicas),
            curr_replicas=int(current_woker_replicas),
            app_name="worker",
        )

    except Exception as e:
        raise e


def read_k8s_yml(file_path: str, file_name: str):
    config.load_kube_config()
    full_path_name = file_path + "/" + file_name
    try:
        with open(full_path_name) as f:
            dep = yaml.safe_load(f)
            return dep
    except Exception as e:
        logger.error(f"cannot open yaml file: {e}")
        raise e


def create_k8s_svc_from_yaml(
    file_path: str, file_name: str, namspace: str = "default"
) -> bool:
    try:
        file_setting = read_k8s_yml(file_path=file_path, file_name=file_name)
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
        logger.error(f"create k8s deployment error: {e}")
        raise e


def replace_k8s_yaml_with_replicas(
    file_path: str, file_name: str, new_replicas: int, app_name: str, curr_replicas: int
) -> bool:
    try:
        file_setting = read_k8s_yml(file_path=file_path, file_name=file_name)
    except Exception as e:
        raise e
    config.load_kube_config()
    apps_v1_api = client.AppsV1Api()

    # origin_replica = dep['spec']['replicas']
    print(f"curr_replicas replcia {curr_replicas}, new_replicas: {new_replicas} ")
    if curr_replicas != new_replicas:
        file_setting["spec"]["replicas"] = int(new_replicas)
        logger.info(
            f" ========= Update {app_name} replicas from {curr_replicas} to {new_replicas} ========= "
        )
        try:
            resp = apps_v1_api.replace_namespaced_deployment(
                name=app_name, body=file_setting, namespace="default"
            )
            print("Replace created. status='%s'" % str(resp.status))
            is_ready = wait_container_ready(
                num_container=new_replicas,
                container_prefix=app_name,
                counter=60,
                delay=1,
            )
            if is_ready is False:
                raise Exception("Wait over time")
            return True
        except Exception as e:
            print(f"no deplyment.yaml or wait over time{e}")
            raise e
