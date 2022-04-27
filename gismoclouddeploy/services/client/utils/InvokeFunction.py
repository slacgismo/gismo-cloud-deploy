from subprocess import PIPE, run
from kubernetes import client, config
from models.Config import Config
def invok_docekr_exec_run_process_file( bucket_name, 
                                        file_path,
                                        file_name, 
                                        column_name, 
                                        solver, 
                                        saved_bucket,
                                        saved_file_path,
                                        saved_filename,
                                        container_type, 
                                        container_name):
    if container_type == "docker":
        command = [ "docker", 
                    "exec",
                    "-it",
                    container_name,
                    "python",
                    "app.py",
                    "process_a_file",
                    f"{bucket_name}",
                    f"{file_path}",
                    f"{file_name}",
                    f"{column_name}",
                    f"{solver}",
                    f"{saved_bucket}",
                    f"{saved_file_path}",
                    f"{saved_filename}",
                    ]
        res = exec_docker_command(command)
        return res
        
    elif container_type == "kubernetes":
        # get pod name
       
        pod_name = get_k8s_pod_name(container_name)
        # print(f" k8s pod_name: {pod_name}")
        # print(f"pod_name: {pod_name}")
        command = [ "kubectl", 
                    "exec",
                    pod_name,
                    "--stdin",
                    "--tty",
                    "--",
                    "python",
                    "app.py",
                    "process_a_file",
                    f"{bucket_name}",
                    f"{file_path}",
                    f"{file_name}",
                    f"{column_name}",
                    f"{solver}",
                    f"{saved_bucket}",
                    f"{saved_file_path}",
                    f"{saved_filename}"
                ]
        res = exec_docker_command(command)
        return res
    else :
        print("no docker image or container found")



def invoke_docker_exec_get_task_status(task_id,container_type,container_name ):
    if container_type == "docker":
        command = ["docker", 
        "exec",
        "-it",
        container_name,
        "python",
        "app.py",
        "get_task_status",
        f"{task_id}"
        ]
        res = exec_docker_command(command)
        r2 = res.replace("\'","\"")
        print(f"res here--->: {r2}")
        return res
    elif container_type == "kubernetes":
        pod_name = get_k8s_pod_name(container_name)
        command = [ "kubectl", 
                    "exec",
                    pod_name,
                    "--stdin",
                    "--tty",
                    "--",
                    "python",
                    "app.py",
                     "get_task_status",
                    f"{task_id}"
                ]
        res = exec_docker_command(command)
        r2 = res.replace("\'","\"")
        print(f"res here--->: {r2}")
        return res



# def invoke_docker_exec_combine_files(bucket_name,source_folder,target_folder,target_filename,container_type,container_name):
def invoke_docker_exec_combine_files(config:Config) -> str:
    if config.container_type == "docker":
        
        command = ["docker", 
        "exec",
        "-it",
        config.container_name,
        "python",
        "app.py",
        "combine_files",
        f"{config.saved_bucket}",
        f"{config.saved_tmp_path}",
        f"{config.saved_target_path}",
        f"{config.saved_target_filename}"
        ]
        print(f"command here--->: {command}")
        res = exec_docker_command(command)
        r2 = res.replace("\'","\"")
        
        return res
    elif config.container_type == "kubernetes":
        pod_name = get_k8s_pod_name(config.container_name)
        command = [ "kubectl", 
                    "exec",
                    pod_name,
                    "--stdin",
                    "--tty",
                    "--",
                    "python",
                    "app.py",
                    "combine_files",
                    f"{config.saved_bucket}",
                    f"{config.saved_tmp_path}",
                    f"{config.saved_target_path}",
                    f"{config.saved_target_filename}",
                ]
        res = exec_docker_command(command)
        r2 = res.replace("\'","\"")
        print(f"res here--->: {r2}")
        return res





def exec_docker_command(command):
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    # print(result.returncode, result.stdout, result.stderr)
    return result.stdout

def get_k8s_pod_name(container_name):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    print("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        # print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
        podname = i.metadata.name.split("-")[0]
        if podname == container_name:
            print(f"podname: {i.metadata.name}")
            return i.metadata.name
