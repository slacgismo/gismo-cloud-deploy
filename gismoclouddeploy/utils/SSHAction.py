import enum



class SSHAction(enum.Enum):
    installation = "installation"
    set_aws_cli = "set_aws_cli"
    upload_foder = "upload_foder"
    upload_file = "upload_file"
    run_files = "run_files"
    ssh ="ssh"

