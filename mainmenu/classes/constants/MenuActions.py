import enum



class MenuActions(enum.Enum):
    
    create_cloud_resources_and_start = "create_cloud_resources_and_start"
    resume_from_existing = "resume_from_existing"
    cleanup_cloud_resources = "cleanup_cloud_resources"
    run_in_local_machine = "run_in_local_machine"
    stop_ec2 = "stop_ec2"
    end_application = "end_application"

