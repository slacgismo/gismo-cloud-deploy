import time
from kubernetes import client, config
import logging
from .k8s_utils import read_k8s_yml

from .invoke_function import (
    invoke_eksctl_scale_node,
)


def num_of_nodes_ready() -> int:
    # print("check node status")
    config.load_kube_config()
    v1 = client.CoreV1Api()
    response = v1.list_node()
    num_of_node_ready = 0
    for node in response.items:
        status = node.status.conditions[-1].status  # only looks the last

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

    else:
        res = invoke_eksctl_scale_node(
            cluster_name=cluster_name,
            group_name=nodegroup_name,
            nodes=num_node,
            nodes_max=num_node,
            nodes_min=num_node,
        )


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


def match_hostname_from_node_name(
    hostname: str = None, pod_prefix: str = "worker"
) -> str:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    # print("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    pods = {}
    for i in ret.items:
        _pod_prefix = i.metadata.name.split("-")[0]
        _pod_name = i.metadata.name
        if _pod_prefix == pod_prefix and _pod_name == hostname:
            _node_name = i.spec.node_name
            return _node_name

    return None


def collect_node_name_and_pod_name(pod_prefix: str = "worker") -> dict:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    # print("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)

    nodes = dict()
    for i in ret.items:
        _pod_prefix = i.metadata.name.split("-")[0]
        _pod_name = i.metadata.name
        if _pod_prefix == pod_prefix:

            _node_name = i.spec.node_name
            nodes[_pod_name] = _node_name

    return nodes


def scale_eks_nodes_and_wait(
    scale_node_num: int = 1,
    total_wait_time: int = 90,
    delay: int = 5,
    cluster_name: str = None,
    nodegroup_name: str = None,
) -> bool:
    try:
        target_node_number = int(scale_node_num)
        logging.info(f" cluster_name: {cluster_name} nodegroup_name:{nodegroup_name} ")
        num_nodes = num_of_nodes_ready()
        logging.info(
            f"scale node {target_node_number}, current node number: {num_nodes}"
        )
        if num_nodes == target_node_number:
            logging.info(
                f"current node number is {num_nodes}, and target node number is {target_node_number}. Scale node success!!!"
            )
            return True
        # num_node is not equal ,
        logging.info(f"scale node num: {target_node_number}")
        scale_node_number(
            min_nodes=target_node_number,
            cluster_name=cluster_name,
            nodegroup_name=nodegroup_name,
        )

        while total_wait_time:
            num_nodes = num_of_nodes_ready()
            logging.info(
                f"waiting {target_node_number} ready , current num_nodes:{num_nodes}  ....counter: {total_wait_time} Time: {time.ctime(time.time())}"
            )
            if num_nodes == target_node_number:
                return True
            total_wait_time -= delay
            time.sleep(delay)
        return False
    except Exception as e:
        logging.error(f"scale node number error: {e}")
        raise e
