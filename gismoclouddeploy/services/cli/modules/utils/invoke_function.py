from subprocess import PIPE, run
from kubernetes import client, config
from server.models.Configurations import Configurations
import subprocess
import sys


def exec_subprocess_command(command: str) -> str:

    process = subprocess.Popen(
        command,
        shell=True,
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    while True:
        realtime_output = process.stdout.readline()
        if realtime_output == "" and process.poll() is not None:
            break
        if realtime_output:
            print(realtime_output.strip(), flush=False)
            sys.stdout.flush()


def exec_docker_command(command: str) -> str:
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    if result.returncode != 0:
        print(result.returncode, result.stdout, result.stderr)
        raise Exception(f"Invalid result: { result.returncode } { result.stderr}")
    print(result.returncode, result.stdout, result.stderr)
    return result.stdout


def invoke_kubectl_delete_all_deployment():
    command = ["kubectl", "delete", "deployment", "--all"]

    res = exec_docker_command(command)
    return res


def invoke_kubectl_delete_deployment(name: str = None) -> str:
    # command = ["kubectl", "delete", "deployment", "f{name}"]
    command = f"kubectl delete deployment {name}"
    output = subprocess.check_output(["bash", "-c", command])

    return output


def invoke_kubectl_apply_file(k8s_path: str = "./k8s/k8s-local", file_name: str = None):
    # command = f"kubectl apply -f {k8s_path}/{file_name}"
    command = ["kubectl", "apply", "-f", f"{k8s_path}/{file_name}"]
    print(f"command: {command}")
    # output = subprocess.check_output(["bash", "-c", str(command)])
    # output =exec_subprocess_command(command=command)
    output = exec_docker_command(command)
    return str(output)


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


def invoke_docker_compose_build() -> str:
    # command = ["docker-compose", "build"]
    command = "docker-compose build"
    output = subprocess.check_output(["bash", "-c", command])
    return output


def invoke_ecr_validation() -> str:
    command = "aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 041414866712.dkr.ecr.us-east-2.amazonaws.com"
    output = subprocess.check_output(["bash", "-c", command])
    print(output)


def invoke_tag_image(image_name: str, image_tag: str, ecr_repo: str) -> str:
    command = f"docker image tag {image_name} {ecr_repo}/{image_name}:{image_tag}"
    output = exec_subprocess_command(command=command)
    print(output)


def invoke_push_image(image_name: str, image_tag: str, ecr_repo: str) -> str:
    command = f"docker push {ecr_repo}/{image_name}:{image_tag}"
    output = exec_subprocess_command(command=command)
    print(output)


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


def invoke_docker_check_image_exist(image_name: str = None):
    try:
        command = f"docker image inspect {image_name}"
        output = subprocess.check_output(["bash", "-c", command])
        return output
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
