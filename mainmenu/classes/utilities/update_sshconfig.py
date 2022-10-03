from genericpath import exists
import logging

from sshconf import read_ssh_config
from os.path import expanduser


def add_public_ip_to_sshconfig(
    public_ip: str, host: str, login_user: str, key_pair_name: str, local_pem_path: str
):
    """
    add new public ip to ssh/config file into a host. If the hose exists in file, the host update it current public ip

    Parameters
    ----------
    :param str public_ip:       interval of fetching public ip of ec2
    :param str host:            host name
    :param str ec2_instance_id: ec2 instance id
    :param str login_user:      ec2 login user
    :param str key_pair_name:   ec2 keypair name
    :param str local_pem_path:  local pem file path
    """
    ssh_confg_file = local_pem_path + "/config"
    if not exists(ssh_confg_file):
        try:
            open(ssh_confg_file, "a").close()
        except OSError:
            logging.info(f"Failed creating the {ssh_confg_file}")
        else:
            logging.info("File created")

    c = read_ssh_config(ssh_confg_file)

    if public_ip is None:
        raise Exception("Public is none")

    if login_user is None:
        raise Exception("login user is none")

    if key_pair_name is None:
        raise Exception("keypair name is none")
    for _host in c.hosts():
        if _host == host:
            logging.info(f"{host} exist in .ssh/config")
            c.set(
                host,
                hostname=public_ip,
                User=login_user,
                IdentityFile=f"{key_pair_name}.pem",
            )
            return
    c.add(
        host, hostname=public_ip, User=login_user, IdentityFile=f"{key_pair_name}.pem"
    )
    logging.info(f"add {public_ip} success")
    c.save()


def delete_public_ip_to_sshconfig(public_ip: str):
    logging.info("Delete public ip to ssh config")
    c = read_ssh_config(expanduser("~/.ssh/config"))
    print("hosts", c.hosts())
    c.remove(public_ip)
    logging.info(f"Remove {public_ip} success")
    c.save()
