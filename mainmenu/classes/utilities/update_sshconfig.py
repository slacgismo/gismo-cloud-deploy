import logging

from sshconf import read_ssh_config
from os.path import expanduser


def add_public_ip_to_sshconfig(
        public_ip:str,
        hostname:str,
        login_user:str,
        key_pair_name:str
    ):

        logging.info("Add public ip to  ssh config")
        c = read_ssh_config(expanduser("~/.ssh/config"))


        if public_ip is None:
            raise Exception ("Public is none")

        if login_user is None:
            raise Exception ("login user is none")
        
        if key_pair_name is None:
            raise Exception ("keypair name is none")
        for host in  c.hosts():
            if host == hostname:
                logging.info(f"{hostname} exist in .ssh/config")
                c.set(public_ip, 
                    hostname=hostname, 
                    User=login_user,
                    IdentityFile=f"{key_pair_name}.pem"
                )
                return
        c.add(public_ip, 
            hostname=hostname, 
            User=login_user,
            IdentityFile=f"{key_pair_name}.pem"
        )
        logging.info(f"add {public_ip} success")
        c.save()

# def update_sshconfig(
#     public_ip:str,
#     hostname:str,
#     login_user:str,
#     key_pair_name:str
# ):
#     c = read_ssh_config(expanduser("~/.ssh/config"))


def delete_public_ip_to_sshconfig(public_ip:str):
    logging.info("Delete public ip to ssh config")
    c = read_ssh_config(expanduser("~/.ssh/config"))
    print("hosts", c.hosts())
    c.remove(public_ip)
    logging.info(f"Remove {public_ip} success")
    c.save()