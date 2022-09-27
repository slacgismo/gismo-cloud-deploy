from asyncio.log import logger

from subprocess import PIPE, run

import subprocess
import sys
import threading




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


def exec_eksctl_create_cluster(cluster_file:str) -> str:
    try:
        command = f"eksctl create cluster -f {cluster_file}"
        output = exec_subprocess_command(command=command)
        return output
    except Exception as e:
        raise e
def exec_eksctl_delete_cluster(cluster_file:str) -> str:
    try:
        command = f"eksctl delete cluster -f {cluster_file}"
        output = exec_subprocess_command(command=command)
        return output
    except Exception as e:
        raise e

def exec_eksctl_update_admin_arn(cluster_name:str, region:str, arn:str) -> str:
    try:
        command = f"eksctl create iamidentitymapping --cluster  {cluster_name} --region={region} --arn {arn} --group system:masters --username admin"
        output = exec_subprocess_command(command=command)
        return output
    except Exception as e:
        raise e

def invoke_kubectl_delete_all_po(namespace:str = "default"):
    command = ["kubectl", "delete", "po", "--all", "-n", f"{namespace}"]

    res = exec_docker_command(command)
    return res

def invoke_kubectl_delete_all_services(namespace:str= "default"):
    command = ["kubectl", "delete", "svc", "--all", "-n" ,f"{namespace}"]

    res = exec_docker_command(command)
    return res

def invoke_kubectl_delete_all_deployment(namespace:str = "default"):
    command = ["kubectl", "delete", "deployment", "--all","-n",f"{namespace}"]

    res = exec_docker_command(command)
    return res

## Create Namespace 
def invoke_kubectl_create_namespaces(namespace:str) -> str:
    command = ["kubectl", "create", "namespace", f"{namespace}"]

    res = exec_docker_command(command)
    return res
## Delete Namespace 
def invoke_kubectl_delete_namespaces(namespace:str) -> str:
    command = ["kubectl", "delete", "namespace", f"{namespace}", "--wait=false"]

    res = exec_docker_command(command)
    return res

def invoke_kubectl_delete_all_from_namspace(namespace:str) -> str:
    command = ["kubectl", "delete","all","--all","-n", f"{namespace}"]
    print(f"command :{command}")
    res = exec_docker_command(command)

    return res
## ===================


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
    project: str = None,
    target_path_of_upload_file :str = None,
    source_path_of_upload_file :str = None,
    
) -> str:
    command = f"WORKER_DIRECTORY={project} docker-compose build --build-arg CODES_FOLDER={project} --build-arg TARGET_PATH_OF_UPLOAD_FILE={target_path_of_upload_file} --build-arg SOURCE_PATH_OF_UPLOAD_FILE={source_path_of_upload_file}"

    print(f"Build command :{command}")
    output = subprocess.check_output(["bash", "-c", command])
    return output



def invoke_ecr_validation(ecr_repo: str) -> str:
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
    print(f"output :{output}")
    return output


def invoke_push_image(image_name: str, image_tag: str, ecr_repo: str) -> str:
    command = f"docker push {ecr_repo}/{image_name}:{image_tag}"
    output = exec_subprocess_command(command=command)



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
    namespace:str = "default",
) -> str:

    command = [
        "docker",
        "exec",
        "-n",
        f"{namespace}"
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
    namespace:str = "default"
) -> str:
    command = [
        "docker",
        "exec",
        "-n",
        f"{namespace}",
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
    namespace:str = "default"
) -> None:
    
    command = [
        "kubectl",
        "exec",
        "-n",
        f"{namespace}",
        pod_name,
        "--stdin",
        "--tty",
        "--",
        "python",
        "app.py",
        "process_files",
        f"{config_params_str}"
    ]
    # print(f"run-fils command: {command}")
    try:

        res = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        # out, err = res.communicate()
        # print(out, err)
        # return out

    except KeyboardInterrupt as e:
        print(f"Invoke k8s process file error:{e}")
        res.terminate()



def invoke_exec_k8s_ping_worker(
    service_name: str = None,
    namespace:str = "default"
) -> str:
    command = [
        "kubectl",
        "exec",
        "-n",
        f"{namespace}",
        service_name,
        "--stdin",
        "--tty",
        "--",
        "python",
        "app.py",
        "ping_worker",
    ]
    print(f"command : {command}")
    res = exec_docker_command(command)
    return res


def invoke_exec_k8s_check_task_status(
    server_name: str = None,
    task_id: str = None,
    namespace :str = "default"
) -> str:
    command = [
        "kubectl",
        "exec",
        "-n",
        f"{namespace}",
        server_name,
        "--stdin",
        "--tty",
        "--",
        "python",
        "app.py",
        "check_task_status",
        f"{task_id}",
    ]
   
    try:
        res = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out, err = res.communicate()
        print(f"------ {out}")
        return out
    except KeyboardInterrupt as e:
        logger.error(f"Invoke k8s process file error:{e}")
        res.terminate()
    return res
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

# kubectl exec --namespace 0-dhcpvisitor21818slacstanfordedu server-65bf8bc584-tzkgr  --stdin --tty -- python app.py ping_worker 
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



def invoke_force_delete_namespace(namespace:str = None):
    try:
        command = f"kubectl get namespace {namespace} -o json > {namespace}.json; sed -i -e 's/\"kubernetes\"//' {namespace}.json; kubectl replace --raw \"/api/v1/namespaces/{namespace}/finalize\" -f ./{namespace}.json"
        output = subprocess.check_output(["bash", "-c", command])
        return output
    except Exception as e:
        raise e


def invoke_delete_all_resource_in_all_namespace():
    command = '''kubectl delete "$(kubectl api-resources --namespaced=true --verbs=delete -o name | tr "\n" "," | sed -e 's/,$//')" --all'''
    output = subprocess.check_output(["bash", "-c", command])
    return output

def invoke_docker_system_prune_all():
    command = 'docker system prune -a -f'
    output = subprocess.check_output(["bash", "-c", command])
    return output

