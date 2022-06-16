import time

from kubernetes import client, config
from server.models.Configurations import Configurations
import logging
from .k8s_utils import get_k8s_pod_info, read_k8s_yml

from modules.utils.invoke_function import (
    invoke_kubectl_apply,
    invoke_eksctl_scale_node,
    invoke_kubectl_rollout,
)

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def num_pod_ready(container_prefix: str) -> int:
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
        if pod_prefix == container_prefix:
            if (
                int(i.metadata.annotations["deployment.kubernetes.io/revision"])
                > max_version
            ):
                max_version = int(
                    i.metadata.annotations["deployment.kubernetes.io/revision"]
                )
                pod_name = i.metadata.name
                ready_replicas = i.status.ready_replicas
    if pod_name is None:
        raise Exception(f"No pod{container_prefix} in list")

    return ready_replicas


def wait_pod_ready(
    num_container: str, container_prefix: str, counter: int, delay: int
) -> bool:
    cunrrent_num_container = 0

    while counter:
        cunrrent_num_container = num_pod_ready(container_prefix=container_prefix)
        if cunrrent_num_container == num_container:
            logger.info(f"{num_container} pods are running")
            return
        counter -= delay
        logger.info(
            f"waiting {container_prefix} {cunrrent_num_container} .counter: {counter - delay} Time: {time.ctime(time.time())}"
        )
        time.sleep(delay)

    raise Exception("Wait over time")


def scale_nodes_and_wait(
    scale_node_num: int, counter: int, delay: int, config_params_obj: Configurations
) -> bool:
    try:
        target_node_number = int(scale_node_num)

        num_nodes = num_of_nodes_ready()
        logger.info(
            f"scale node {target_node_number}, current node number: {num_nodes}"
        )
        if num_nodes == target_node_number:
            logger.info(
                f"current node number is {num_nodes}, and target node number is {target_node_number}. Scale node success!!!"
            )
            return True
        # num_node is not equal ,
        logger.info(f"scale node num: {target_node_number}")
        scale_node_number(
            min_nodes=target_node_number,
            cluster_name=config_params_obj.cluster_name,
            nodegroup_name=config_params_obj.nodegroup_name,
        )

        while counter:
            num_nodes = num_of_nodes_ready()
            print(
                f"waiting {target_node_number} ready , current num_nodes:{num_nodes}  ....counter: {counter} Time: {time.ctime(time.time())}"
            )
            if num_nodes == target_node_number:
                return True
            counter -= delay
            time.sleep(delay)
        return False
    except Exception as e:
        logger.error(f"scale node number error: {e}")
        return False


def num_of_nodes_ready() -> int:
    # print("check node status")
    config.load_kube_config()
    v1 = client.CoreV1Api()
    response = v1.list_node()
    num_of_node_ready = 0
    for node in response.items:

        # print(node.metadata.labels['kubernetes.io/hostname'])
        # cluster = node.metadata.labels["alpha.eksctl.io/cluster-name"]
        # nodegroup = node.metadata.labels["alpha.eksctl.io/nodegroup-name"]
        # hostname = node.metadata.labels["kubernetes.io/hostname"]
        # instance_type = node.metadata.labels["beta.kubernetes.io/instance-type"]
        # region = node.metadata.labels["topology.kubernetes.io/region"]
        status = node.status.conditions[-1].status  # only looks the last
        # status_type = node.status.conditions[-1].type  # only looks the last
        if bool(status) is True:
            num_of_node_ready += 1
    return num_of_node_ready


def scale_node_number(min_nodes: int, cluster_name: str, nodegroup_name: str):
    # check if input is integer
    # assert(type(min_nodes) is int, f"Input {min_nodes} is not an")
    # gcd-node-group-lt
    try:
        num_node = int(min_nodes)
    except Exception as e:
        print(f"Error: input {min_nodes} is not a integer: {e}")
        return False

    if num_node == 0:

        res = invoke_eksctl_scale_node(
            cluster_name=cluster_name,
            group_name=nodegroup_name,
            nodes=0,
            nodes_max=1,
            nodes_min=0,
        )
        print(f"scale down to {num_node}, res: {res}")
    else:
        res = invoke_eksctl_scale_node(
            cluster_name=cluster_name,
            group_name=nodegroup_name,
            nodes=num_node,
            nodes_max=num_node,
            nodes_min=num_node,
        )
        print(f"scale up to {num_node}, res:{res}")


def match_pod_ip_to_node_name(pods_name_sets: set) -> dict:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    # print("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    pods = {}
    for i in ret.items:
        podname = i.metadata.name.split("-")[0]
        if podname in pods_name_sets:
            _pod_name = i.metadata.name
            _node_name = i.spec.node_name
            ip = i.status.pod_ip
            pods[ip] = dict(POD_NAME=_pod_name, NOD_NAME=_node_name)
    return pods


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
            is_ready = wait_pod_ready(
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


def create_or_update_k8s(
    config_params_obj: Configurations,
    rollout: bool = True,
    env: str = "local",
    image_tag: str = "latest",
):
    """Read worker config, if the replicas of woker is between from config.yaml and k8s/k8s-aws or k8s/k8s-local
    Update the replicas number
    """
    k8s_path = ""
    try:
        if env == "local":
            k8s_path = "./k8s/k8s-local"
        else:
            k8s_path = "./k8s/k8s-aws"
    except Exception as e:
        raise Exception(f"K8s path not exist {e}")

    logger.info(" ========= Check K8s is status ========= ")
    # deployment_pod_name_list = ["worker", "webapp", "redis", "rabbitmq"]
    deployment_services_list = config_params_obj.deployment_services_list
    logger.info(deployment_services_list)
    apply_k8s_flag = False
    # if one of the pod is missing , re init all the k8s services
    for pod_name in deployment_services_list:
        pod_info = get_k8s_pod_info(prefix=pod_name)
        if pod_info["pod_name"] is None:
            apply_k8s_flag = True
            break

    if apply_k8s_flag:
        # invoke kubectl apply -f .(folder)
        response = invoke_kubectl_apply(k8s_path)

        # wait pod ready
        for pod_name in deployment_services_list:
            pod_info = get_k8s_pod_info(prefix=pod_name)
            if pod_name == "worker":
                try:
                    worker_setting = read_k8s_yml(
                        file_path=k8s_path, file_name="worker.deployment.yaml"
                    )
                except Exception as e:
                    raise e
                worker_default_replicas = worker_setting["spec"]["replicas"]
                is_pod_ready = wait_pod_ready(
                    num_container=worker_default_replicas,
                    container_prefix=pod_name,
                    counter=60,
                    delay=1,
                )
                if is_pod_ready is False:
                    logger.error(f"Waiting {pod_name} pod ready over time")
                    raise Exception("Waiting over time")
            else:
                is_pod_ready = wait_pod_ready(
                    num_container=1, container_prefix=pod_name, counter=60, delay=1
                )
                if is_pod_ready is False:
                    logger.error(f"Waiting {pod_name} pod ready over time")
                    raise Exception("Waiting over time")

    logger.info(" ========= Compare k8s Worker Setting with config.yaml ========= ")

    current_woker_replicas = num_pod_ready(container_prefix="worker")

    if (
        current_woker_replicas == int(config_params_obj.worker_replicas)
        and rollout is False
    ):
        logger.info("current worker replicas = config_params_obj.worker_replicas ")
        return

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
    if rollout:
        logger.info(" ========= Rollout and restart ========= ")
        # rollout_pod_list = ["webapp", "worker"]

        for pod_name in deployment_services_list:
            esponse = invoke_kubectl_rollout(podprefix=pod_name)
            logger.info(esponse)
        # wait 30 second
        wait_time = 25
        while wait_time >= 0:
            logger.info(f"wait pod restart :{wait_time}")
            wait_time -= 1
            time.sleep(1)

        for pod_name in deployment_services_list:
            if pod_name == "worker":
                is_pod_ready = wait_pod_ready(
                    num_container=int(config_params_obj.worker_replicas),
                    container_prefix=pod_name,
                    counter=60,
                    delay=1,
                )
                if is_pod_ready is False:
                    logger.error(f"Waiting {pod_name} pod ready over time")
                    raise Exception("Waiting over time")
            else:
                is_pod_ready = wait_pod_ready(
                    num_container=1, container_prefix=pod_name, counter=60, delay=1
                )
                if is_pod_ready is False:
                    logger.error(f"Waiting {pod_name} pod ready over time")
                    raise Exception("Waiting over time")


def scale_eks_nodes_and_wait(
    scale_node_num: int = 1,
    total_wait_time: int = 60,
    delay: int = 1,
    cluster_name: str = None,
    nodegroup_name: str = None,
) -> bool:
    try:
        target_node_number = int(scale_node_num)

        num_nodes = num_of_nodes_ready()
        logger.info(
            f"scale node {target_node_number}, current node number: {num_nodes}"
        )
        if num_nodes == target_node_number:
            logger.info(
                f"current node number is {num_nodes}, and target node number is {target_node_number}. Scale node success!!!"
            )
            return True
        # num_node is not equal ,
        logger.info(f"scale node num: {target_node_number}")
        scale_node_number(
            min_nodes=target_node_number,
            cluster_name=cluster_name,
            nodegroup_name=nodegroup_name,
        )

        while total_wait_time:
            num_nodes = num_of_nodes_ready()
            print(
                f"waiting {target_node_number} ready , current num_nodes:{num_nodes}  ....counter: {total_wait_time} Time: {time.ctime(time.time())}"
            )
            if num_nodes == target_node_number:
                return True
            total_wait_time -= delay
            time.sleep(delay)
        return False
    except Exception as e:
        logger.error(f"scale node number error: {e}")
        return False
