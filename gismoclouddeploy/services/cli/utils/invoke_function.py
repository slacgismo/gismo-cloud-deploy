from subprocess import PIPE, run
from kubernetes import client, config
from models.Config import Config
from models.SolarParams import SolarParams
from models.Config import Config
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def exec_docker_command(command):
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    if result.returncode != 0:
        print(result.returncode, result.stdout, result.stderr)
        raise Exception(f"Invalid result: { result.returncode } { result.stderr}")
    print(result.returncode, result.stdout, result.stderr)
    return result.stdout


def invoke_kubectl_apply(folder: str = "../k8s/k8s-local"):
    command = ["kubectl", "apply", "-f", f"{folder}"]

    res = exec_docker_command(command)
    return res


def invoke_eksctl_scale_node(
    cluster_name: str, group_name: str, nodes: int, nodes_max: int, nodes_min: int
):
    command = [
        "eksctl",
        "scale",
        "nodegroup",
        "--cluster",
        cluster_name,
        "--name",
        group_name,
        "--nodes",
        str(nodes),
        "--nodes-max",
        str(nodes_max),
        "--nodes-min",
        str(nodes_min),
    ]

    res = exec_docker_command(command)
    return res


# eksctl scale nodegroup --cluster gcd-eks-cluster --name gcd-node-group-lt --nodes 0 --nodes-max 1 --nodes-min 0


def invoke_docekr_exec_run_process_first_n_files(
    config_obj: Config,
    solarParams_obj: SolarParams,
    first_n_files: int,
    container_type: str,
    container_name: str,
):
    solardata_params_str = solarParams_obj.parse_solardata_params_to_json_str()
    config_params_str = config_obj.parse_config_to_json_str()

    if container_type == "docker":
        command = [
            "docker",
            "exec",
            "-it",
            container_name,
            "python",
            "app.py",
            "process_first_n_files",
            f"{config_params_str}",
            f"{solardata_params_str}",
            f"{first_n_files}",
        ]

    elif container_type == "kubernetes":
        # get pod name

        pod_name = get_k8s_pod_name(container_name)
        command = [
            "kubectl",
            "exec",
            pod_name,
            "--stdin",
            "--tty",
            "--",
            "python",
            "app.py",
            "process_first_n_files",
            f"{config_params_str}",
            f"{solardata_params_str}",
            f"{first_n_files}",
        ]
    try:
        res = exec_docker_command(command)
        return res
    except Exception as e:
        raise e


def invoke_docekr_exec_revoke_task(
    task_id: str, container_type: str, container_name: str
):

    if container_type == "docker":
        command = [
            "docker",
            "exec",
            "-it",
            container_name,
            "python",
            "app.py",
            "revoke_task",
            f"{task_id}",
        ]

    elif container_type == "kubernetes":
        pod_name = get_k8s_pod_name(container_name)
        command = [
            "kubectl",
            "exec",
            pod_name,
            "--stdin",
            "--tty",
            "--",
            "python",
            "app.py",
            "revoke_task",
            f"{task_id}",
        ]
    try:
        res = exec_docker_command(command)
        return res
    except Exception as e:
        raise e


# def invoke_docekr_exec_run_process_files(config_obj:Config  ,
#                                         solarParams_obj: SolarParams,
#                                         container_type:str,
#                                         container_name:str):
#     solardata_params_str = solarParams_obj.parse_solardata_params_to_json_str()
#     config_params_str = config_obj.parse_config_to_json_str()
#     print(f"config_obj:{config_obj.dynamodb_tablename}")

#     if container_type == "docker":
#         command = [ "docker",
#                     "exec",
#                     "-it",
#                     container_name,
#                     "python",
#                     "app.py",
#                     "process_files",
#                     f"{config_params_str}",
#                     f"{solardata_params_str}",
#                     ]

#     elif container_type == "kubernetes":
#         # get pod name

#         pod_name = get_k8s_pod_name(container_name)
#         # print(f" k8s pod_name: {pod_name}")
#         # print(f"pod_name: {pod_name}")
#         command = [ "kubectl",
#                     "exec",
#                     pod_name,
#                     "--stdin",
#                     "--tty",
#                     "--",
#                     "python",
#                     "app.py",
#                     "process_files",
#                     f"{config_params_str}",
#                     f"{solardata_params_str}"
#                 ]
#     try:
#         res = exec_docker_command(command)
#         return res
#     except Exception as e:
#         raise e


# def invoke_docker_exec_get_task_status(task_id,container_type,container_name ):
#     if container_type == "docker":
#         command = ["docker",
#         "exec",
#         "-it",
#         container_name,
#         "python",
#         "app.py",
#         "get_task_status",
#         f"{task_id}"
#         ]
#         res = exec_docker_command(command)
#         r2 = res.replace("\'","\"")
#         # print(f"res here--->: {r2}")
#         return res
#     elif container_type == "kubernetes":
#         pod_name = get_k8s_pod_name(container_name)
#         command = [ "kubectl",
#                     "exec",
#                     pod_name,
#                     "--stdin",
#                     "--tty",
#                     "--",
#                     "python",
#                     "app.py",
#                      "get_task_status",
#                     f"{task_id}"
#                 ]
#         res = exec_docker_command(command)
#         r2 = res.replace("\'","\"")
#         # print(f"res here--->: {r2}")
#         return res


# def invoke_docker_exec_combine_files(bucket_name,source_folder,target_folder,target_filename,container_type,container_name):
# def invoke_docker_exec_combine_files(config:Config) -> str:
#     if config.container_type == "docker":

#         command = ["docker",
#         "exec",
#         "-it",
#         config.container_name,
#         "python",
#         "app.py",
#         "combine_files",
#         f"{config.saved_bucket}",
#         f"{config.saved_tmp_path}",
#         f"{config.saved_target_path}",
#         f"{config.saved_target_filename}"
#         ]
#         print(f"command here--->: {command}")
#         res = exec_docker_command(command)
#         r2 = res.replace("\'","\"")

#         return res
#     elif config.container_type == "kubernetes":
#         pod_name = get_k8s_pod_name(config.container_name)
#         command = [ "kubectl",
#                     "exec",
#                     pod_name,
#                     "--stdin",
#                     "--tty",
#                     "--",
#                     "python",
#                     "app.py",
#                     "combine_files",
#                     f"{config.saved_bucket}",
#                     f"{config.saved_tmp_path}",
#                     f"{config.saved_target_path}",
#                     f"{config.saved_target_filename}",
#                 ]
#         res = exec_docker_command(command)
#         r2 = res.replace("\'","\"")
#         print(f"res here--->: {r2}")
#         return res


def get_k8s_pod_name(container_name):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    # print("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        # print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
        podname = i.metadata.name.split("-")[0]
        if podname == container_name:
            # print(f"podname: {i.metadata.name}")
            return i.metadata.name
