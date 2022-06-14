from subprocess import PIPE, run
from kubernetes import client, config
from server.models.Configurations import Configurations


def exec_docker_command(command: str) -> str:
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


def invoke_kubectl_rollout(podprefix: str = None):
    if podprefix is None:
        return
    command = ["kubectl", "rollout", "restart", f"deployment/{podprefix}"]

    res = exec_docker_command(command)
    return res


def invoke_eksctl_scale_node(
    cluster_name: str, group_name: str, nodes: int, nodes_max: int, nodes_min: int
) -> str:
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


def invoke_exec_run_process_files(
    config_params_str: str, container_type: str, container_name: str, first_n_files: str
) -> str:

    if container_type == "docker":
        command = [
            "docker",
            "exec",
            "-it",
            container_name,
            "python",
            "app.py",
            "process_files",
            f"{config_params_str}",
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
            "process_files",
            f"{config_params_str}",
            f"{first_n_files}",
        ]
    try:
        res = exec_docker_command(command)
        return res
    except Exception as e:
        raise e


def invoke_docekr_exec_revoke_task(
    task_id: str, container_type: str, container_name: str
) -> str:

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


def get_k8s_pod_name(container_name: str) -> str:
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
