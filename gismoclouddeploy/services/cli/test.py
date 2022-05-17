# import asyncio

# async def run(cmd: str):
#     proc = await asyncio.create_subprocess_shell(
#         cmd,
#         stderr=asyncio.subprocess.PIPE,
#         stdout=asyncio.subprocess.PIPE
#     )

#     stdout, stderr = await proc.communicate()

#     print(f'[{cmd!r} exited with {proc.returncode}]')
#     if stdout:
#         print(f'[stdout]\n{stdout.decode()}')
#     if stderr:
#         print(f'[stderr]\n{stderr.decode()}')
# task_id="4f498d17-89cc-434a-8e2e-4bb9590259dc"
# for i in [2,3,3]:
#     asyncio.run(run(f'docker exec -it web python app.py get_task_status {task_id}'))
# # 4f498d17-89cc-434a-8e2e-4bb9590259dc

import platform, os 
import psutil 
def cpu_info(): 
    if platform.system() == 'Windows': 
        return platform.processor() 
    elif platform.system() == 'Darwin': 
        command = '/usr/sbin/sysctl -n machdep.cpu.brand_string' 
        return os.popen(command).read().strip() 
    elif platform.system() == 'Linux': 
        command = 'cat /proc/cpuinfo' 
        return os.popen(command).read().strip() 
    return 'platform not identified' 
 
# print(cpu_info()) 

print(psutil.Process().pid)
print(os.getpid())