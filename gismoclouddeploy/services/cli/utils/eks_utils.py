import time
import logging
from kubernetes import client, config
from utils.aws_utils import check_environment_is_aws
from utils.InvokeFunction import (
    invoke_eksctl_scale_node,
)

import logging 

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')


def num_container_ready(container_prefix:str) -> int:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    num_container_running = 0 
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        podname = i.metadata.name.split("-")[0]
        if podname == container_prefix:
            print("%s\t%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name, i.status.phase))
            if i.status.phase == "Running":
                num_container_running += 1

    return num_container_running

def wait_container_ready(num_container:str, container_prefix:str, counter: int, delay:int) -> bool:
    cunrrent_num_container = 0
    while counter:
        cunrrent_num_container = num_container_ready(container_prefix = container_prefix)
        if cunrrent_num_container == num_container:
            logger.info(f"{num_container} pods are running")
            return True
        counter -= delay
        time.sleep(delay)
    return False

def scale_nodes_and_wait(scale_node_num:str, counter:int, delay:int) -> bool:
    
    num_nodes = num_of_nodes_ready()
    print(f"scale node {scale_node_num}, current node number: {num_nodes}")
    if num_nodes == scale_node_num:
        logger.info(f"{num_nodes} nodes is ready ")
        return True 
    # num_node is not equal ,
    logger.info(f"scale node num: {scale_node_num}")
    scale_node_number(scale_node_num)
    while counter:
        num_nodes = num_of_nodes_ready()
        print(f"waiting {scale_node_num} ready , current num_nodes:{num_nodes}  ....counter: {counter} Time: {time.ctime(time.time())}")
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
        cluster = node.metadata.labels['alpha.eksctl.io/cluster-name']
        nodegroup = node.metadata.labels['alpha.eksctl.io/nodegroup-name']
        hostname = node.metadata.labels['kubernetes.io/hostname']
        instance_type = node.metadata.labels['beta.kubernetes.io/instance-type']
        region = node.metadata.labels['topology.kubernetes.io/region']
        status = node.status.conditions[-1].status # only looks the last 
        status_type = node.status.conditions[-1].type # only looks the last
        if bool(status) == True:
            num_of_node_ready += 1
    return num_of_node_ready


def scale_node_number(min_nodes):
    # check if input is integer
    # assert(type(min_nodes) is int, f"Input {min_nodes} is not an")
    try: 
        node = int(min_nodes)
    except Exception as e:
        print(f"Error: input {min_nodes} is not a integer")
        return False

    # return if running in AWS
    if check_environment_is_aws() != True:
        return False
    if int(min_nodes) == 0 :
     
        res = invoke_eksctl_scale_node(cluster_name="gcd-eks-cluster",
                                        group_name="gcd-node-group-lt",
                                        nodes=0,
                                        nodes_max=1,
                                        nodes_min=0)
        print(f"scale down to {min_nodes}, res: {res}")
    else:
        res = invoke_eksctl_scale_node(cluster_name="gcd-eks-cluster",
                                        group_name="gcd-node-group-lt",
                                        nodes=min_nodes,
                                        nodes_max=min_nodes,
                                        nodes_min=min_nodes)
        print(f"scale up to {min_nodes}, res:{res}")
