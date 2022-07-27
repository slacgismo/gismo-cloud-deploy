from asyncio.log import logger

from subprocess import PIPE, run

import subprocess
import sys
import threading

from numpy import str_


class Command(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None

    def run(self, timeout=0, **kwargs):
        def target(**kwargs):
            self.process = subprocess.Popen(self.cmd, **kwargs)
            self.process.communicate()

        thread = threading.Thread(target=target, kwargs=kwargs)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()

        return self.process.returncode


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
        # print(result.returncode, result.stdout, result.stderr)
        raise Exception(f"Invalid result: { result.returncode } { result.stderr}")
    # print(result.returncode, result.stdout, result.stderr)
    return result.stdout


def invoke_kubectl_delete_all_services():
    command = ["kubectl", "delete", "svc", "--all"]

    res = exec_docker_command(command)
    return res


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
    command = ["kubectl", "apply", "-f", f"{k8s_path}/{file_name}"]
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


def invoke_docker_compose_down_and_remove() -> str:
    command = "docker-compose down --rmi local"
    output = subprocess.check_output(["bash", "-c", command])
    return output


def invoke_docker_compose_up() -> str:
    command = "docker-compose up -d"
    output = subprocess.check_output(["bash", "-c", command])
    return output


def invoke_docker_compose_build(
    code_template_folder: str = None, worker_folder: str = None
) -> str:

    command = f"WORKER_DIRECTORY={worker_folder} docker-compose build --build-arg CODES_FOLDER={code_template_folder}"
    # output = subprocess.check_output(["bash", "-c", command])
    logger.info(f"docker build command: {command}")
    output = exec_subprocess_command(command=command)
    return output


def invoke_ecr_validation(ecr_repo: str_) -> str:
    command = f"aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin {ecr_repo}"
    output = subprocess.check_output(["bash", "-c", command])
    return output


def invoke_tag_image(
    origin_image: str,
    update_image: str,
    image_tag: str,
) -> str:
    command = f"docker image tag {origin_image} {update_image}:{image_tag}"
    output = exec_subprocess_command(command=command)
    return output


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
    ]

    res = exec_docker_command(command)
    return res


def invoke_exec_docker_run_process_files(
    config_params_str: str = None,
    image_name: str = None,
    first_n_files: str = None,
) -> str:

    command = [
        "docker",
        "exec",
        "-it",
        image_name,
        "python",
        "app.py",
        "process_files",
        f"{config_params_str}",
        f"{first_n_files}",
    ]
    try:
        # print(command)
        res = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        # out, err = res.communicate()
    except KeyboardInterrupt as e:
        logger.error(f"Invoke process file error:{e}")
        # res.terminate()
    # print("output")
    # print(out)
    return res
    # res = exec_docker_command(command)
    # return res


def invoke_exec_docker_ping_worker(
    service_name: str = None,
) -> str:

    command = [
        "docker",
        "exec",
        "-it",
        service_name,
        "python",
        "app.py",
        "ping_worker",
    ]
    res = exec_docker_command(command)
    return res


def invoke_exec_docker_check_task_status(
    server_name: str = None,
    task_id: str = None,
) -> str:
    command = [
        "docker",
        "exec",
        "-it",
        server_name,
        "python",
        "app.py",
        "check_task_status",
        f"{task_id}",
    ]
    res = exec_docker_command(command)
    return res


def invoke_eks_updagte_kubeconfig(cluster_name: str = None) -> str:
    print("exec aws eks update-kubeconfig")
    command = f"aws eks update-kubeconfig --name {cluster_name}"
    output = exec_subprocess_command(command=command)
    print(output)


def invoke_eks_get_cluster() -> str:
    print("exec eksctl get cluster")
    command = f"eksctl get cluster"
    output = exec_subprocess_command(command=command)
    print(output)


def invoke_exec_k8s_run_process_files(
    config_params_str: str = None,
    pod_name: str = None,
    first_n_files: str = None,
) -> None:

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
        res = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        # out, err = res.communicate()
        # print(out)
        # return out
        # print(res)
    except KeyboardInterrupt as e:
        logger.error(f"Invoke k8s process file error:{e}")
        res.terminate()
    return res
    # return out
    # res = exec_subprocess_command(command=command)
    # res = exec_docker_command(command)
    # return
    # return res


def invoke_exec_k8s_ping_worker(
    service_name: str = None,
) -> str:
    command = [
        "kubectl",
        "exec",
        service_name,
        "--stdin",
        "--tty",
        "--",
        "python",
        "app.py",
        "ping_worker",
    ]

    res = exec_docker_command(command)
    return res


def invoke_exec_k8s_check_task_status(
    server_name: str = None,
    task_id: str = None,
) -> str:
    command = [
        "kubectl",
        "exec",
        server_name,
        "--stdin",
        "--tty",
        "--",
        "python",
        "app.py",
        "check_task_status",
        f"{task_id}",
    ]
    # try:
    #     res = subprocess.Popen(
    #         command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    #     )
    #     out, err = res.communicate()
    #     print(out)
    #     return out
    # except KeyboardInterrupt as e:
    #     logger.error(f"Invoke k8s process file error:{e}")
    #     res.terminate()
    # return res
    res = exec_docker_command(command)
    print(res)
    return res


def invoke_docekr_exec_revoke_task(image_name: str = None, task_id: str = None) -> str:

    command = [
        "docker",
        "exec",
        "-it",
        image_name,
        "python",
        "app.py",
        "revoke_task",
        f"{task_id}",
    ]
    res = exec_docker_command(command)
    return res


def invoke_ks8_exec_revoke_task(pod_name: str = None, task_id: str = None) -> str:

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
    res = exec_docker_command(command)
    return res


def invoke_docker_check_image_exist(image_name: str = None):
    try:
        command = f"docker image inspect {image_name}"
        output = subprocess.check_output(["bash", "-c", command])
        return output
    except Exception as e:
        raise e


def invoke_check_docker_services():
    command = "docker ps -q"
    output = subprocess.check_output(["bash", "-c", command])
    return output
