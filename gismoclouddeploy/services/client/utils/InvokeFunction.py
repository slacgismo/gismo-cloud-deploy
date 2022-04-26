from subprocess import PIPE, run

def invok_docekr_exec_run_process_file( bucket_name, 
                                        file_path,
                                        file_name, 
                                        column_name, 
                                        solver, 
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
                    f"{solver}"
                    ]
        res = exec_docker_command(command)
        return res
        
    elif container_type == "kubernetes":
        # get pod name
        
        pod_name = get_k8s_pod_name(container_name)
        print(f"pod_name: {pod_name}")
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
                    f"{solver}"
                ]
        res = exec_docker_command(command)
        return res
    else :
        print("no docker image or container found")



def invoke_docker_exec_get_task_status(task_id):
    command = ["docker", 
    "exec",
    "-it",
     "web",
     "python",
     "app.py",
     "get_task_status",
    f"{task_id}"
     ]
    res = exec_docker_command(command)
    r2 = res.replace("\'","\"")
    print(f"res here--->: {r2}")
    return res

def exec_docker_command(command):
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    # print(result.returncode, result.stdout, result.stderr)
    return result.stdout