from email.policy import default
from genericpath import exists
import json
from re import L
import time
from kubernetes import client, config

from typing import Tuple
import logging
import yaml
from typing import List
from datetime import datetime

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

    print(f"create_k8s_deployment_from_yaml {service_name} namspace :{namspace}, file_name:{file_name}")
    print("--------------------------")
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
    print("----------------------------")
    print(f"update yaml file :namspace {namspace}")

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

    # ehceck daemonset or deployment 
    kind = file_setting["kind"]
            
    config.load_kube_config()
    apps_v1_api = client.AppsV1Api()
    if kind == "Deployment":
        print(f"------> apply deployment {image_url_tag} namspace: {namspace}")
        try:
            resp = apps_v1_api.create_namespaced_deployment(
                body=file_setting, namespace=namspace
            )
            # print("Created. status='%s'" % str(resp.status))
            return True
        except Exception as e:
            logger.error(f"create k8s deployment error: {e}")
            raise e
    elif kind == "DaemonSet":
        print(f"apply damentset {image_url_tag}")
        try:
            resp = apps_v1_api.create_namespaced_daemon_set(
                body=file_setting, namespace=namspace
            )
            # print("Created. status='%s'" % str(resp.status))
            return True
        except Exception as e:
            logger.error(f"create k8s daemon set error: {e}")
            raise e

def get_k8s_deployment(prefix: str = None) -> str:
    config.load_kube_config()
    v1 = client.AppsV1Api()
    resp = v1.list_namespaced_deployment(namespace="default")
    dep = []
    for i in resp.items:
        if i.metadata.name == prefix:
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


def get_k8s_image_and_tag_from_deployment(prefix: str = None, namespace:str = "default") -> Tuple[str, str, str]:
    try:
        config.load_kube_config()
        v1 = client.AppsV1Api()
        resp = v1.list_namespaced_deployment(namespace=namespace)
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


def check_k8s_services_exists(name: str = None, namspace:str = "default") -> bool:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    # resp = v1.list_service_for_all_namespaces(watch=False)
    resp = v1.list_namespaced_service(namespace=namspace)
    for i in resp.items:
        if i.metadata.name == name:
            return True
    return False


def get_k8s_pod_name(pod_name: str = None) -> List[dict]:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    ret = v1.list_pod_for_all_namespaces(watch=False)
    pods = []
    # while counter > 0 :
    for i in ret.items:
        status = i.status.conditions[-1].status
        podname = i.metadata.name.split("-")[0]
        if podname == pod_name:
            # status = i.status.conditions
            name = i.metadata.name

            # state = i.status.container_statuses[-1].state
            ready = i.status.container_statuses[-1].ready
            if ready is True:
                # if it's ready
                started_at = i.status.container_statuses[-1].state.running.started_at
                status = i.status
                pod_info = {"name": name, "started_at": started_at}
                pods.append(pod_info)

    # only get the latest server
    if len(pods) > 0:
        max_date = pods[0]["started_at"]
        latest_server_pod_name = pods[0]["name"]
        for pod in pods:
            if max_date < pod["started_at"]:
                max_date = pod["started_at"]
                latest_server_pod_name = pod["name"]
        return latest_server_pod_name

    return None

def get_k8s_pod_name_from_namespace (pod_name_prefix:str = None, namespace:str = "default") -> str:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    ret = v1.list_namespaced_pod(namespace)
    pods = []
    for i in ret.items:    
        status = i.status.conditions[-1].status
        podname = i.metadata.name.split("-")[0]
        if podname == pod_name_prefix:
            # status = i.status.conditions
            name = i.metadata.name
            ready = i.status.container_statuses[-1].ready
            
            if ready is True:
                # if it's ready
                started_at = i.status.container_statuses[-1].state.running.started_at
                status = i.status
                timestamp =  started_at.timestamp()
                pod_info = {"name": name, "timestamp": timestamp}
                pods.append(pod_info)
    sort_orders = sorted(pods, key=lambda d: d['timestamp'], reverse=True) 
    if len(sort_orders) > 0 :
        res = [ sub['name'] for sub in sort_orders ][0]
        print(f"----------- get first k8s_pod_name :{ res}")
        return res

    return None

# def log_k8s_pod_name_from_namespace(pod_name_prefix:str = None, namespace:str = "default") -> str:
#     config.load_kube_config()
#     v1 = client.CoreV1Api()
#     ret = v1.list_namespaced_pod(namespace)
#     pods = []
#     for i in ret.items:    
#         status = i.status.conditions[-1].status
#         podname = i.metadata.name.split("-")[0]
#         if podname == pod_name_prefix:
#             # status = i.status.conditions
#             name = i.metadata.name
    
    




def k8s_create_namespace(namespace:str = None):
    if namespace is None:
        logger.error("namespace is None")
        return 
    if not check_k8s_namespace_exits(namespace):
        ns = client.V1Namespace()
        ns.metadata = client.V1ObjectMeta(name=namespace)
        v1 = client.CoreV1Api()
        v1.create_namespace(ns)
        logging.info(f'Created namespace "{namespace}"')
        logging.debug((json.dumps(ns.metadata, default=str)))

    
    return 




def k8s_delete_namespace(namespace:str = None):
    if namespace is None:
        logger.error("namespace is None")
        return 

    if check_k8s_namespace_exits(namespace):
        logger.info(f"Delete {namespace} ")
    else:
        logger.info(f"No {namespace} exists ")
    return 
    

def check_k8s_namespace_exits(namespace:str = None) -> bool:
    config.load_kube_config()
    v1 = client.CoreV1Api() 
    ret = v1.list_namespace()
    for i in ret.items:    
        name = i.metadata.name
        if name == namespace:
            logger.info(f"{namespace} already exits")
            return True
    return False
def k8s_list_all_namespace():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    ret = v1.list_namespace()
    
    print(ret)

# def get_k8s_pod_name_list(pod_name: str = None, number_server: int = 1) -> List[dict]:
#     config.load_kube_config()
#     v1 = client.CoreV1Api()
#     ret = v1.list_pod_for_all_namespaces(watch=False)
#     pods = []
#     # while counter > 0 :
    # for i in ret.items:
    #     status = i.status.conditions[-1].status
    #     podname = i.metadata.name.split("-")[0]
    #     if podname == pod_name:
    #         # status = i.status.conditions
    #         name = i.metadata.name
   

    #         # state = i.status.container_statuses[-1].state
    #         ready = i.status.container_statuses[-1].ready
    #         if ready is True:
    #             # if it's ready
    #             started_at = i.status.container_statuses[-1].state.running.started_at
    #             status = i.status
    #             # print("==========")
    #             # print(f"started_at {type(started_at)}")
    #             timestamp =  started_at.timestamp()
    #             # print(f"timestamp :{timestamp}")
    #             # res = re.search('\(([^)]+)', str(started_at)).group(1)
    #             # year, month, day, hours, minutes, sec, tz = res.split(', ')
    #             # dattime_string = f"{year}/{month}/{day} {hours}:{minutes}:{sec}"
    #             # print(dattime_string)
    #             # timestamp = time.mktime(datetime.datetime.strptime(dattime_string, "%Y/%m/%d %H:%M:%S").timetuple())
    #             # print(timestamp)
    #             pod_info = {"name": name, "timestamp": timestamp}
    #             pods.append(pod_info)
    # sort_orders = sorted(pods, key=lambda d: d['timestamp'], reverse=True) 

    # if len(sort_orders) >= number_server :
    #     _list =  sort_orders[0:number_server]
    #     res = [ sub['name'] for sub in _list ]
    #     print(f"----------- get_k8s_pod_name_list :{ res}")
    #     return res
#     return sort_orders
#     # only get the latest server
#     # if len(pods) > 0:
#     #     max_date = pods[0]["started_at"]
#     #     latest_server_pod_name = pods[0]["name"]
#     #     for pod in pods:
#     #         if max_date < pod["started_at"]:
#     #             max_date = pod["started_at"]
#     #             latest_server_pod_name = pod["name"]
#     #     return latest_server_pod_name

#     # return None


# def get_cluster_name(namespace:str):
#     clusters_info = []
#     d1  = {}
#     config.load_kube_config()
#     #config.load_incluster_config()
#     configuration = client.Configuration()
#     api_instance = client.AppsV1beta2Api(client.ApiClient(configuration))
#     try:
#         api_response = api_instance.list_namespaced_stateful_set(namespace)
#         for cluster in api_response.items:
#             d1['name']=cluster.metadata.labels['operator.io/cluster']
#             clusters_info.append(d1.copy())
#         return clusters_info
#     except ApiException as e:
#         return "Exception when calling AppsV1beta2Api->patch_namespaced_stateful_set_status: %s\n" % e
