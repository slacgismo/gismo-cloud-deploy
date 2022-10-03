import enum


class InputDescriptions(enum.Enum):
    input_project_name_in_tags = "Enter the name of the project. The project name is listed in all created cloud resources, and it is used for managing a budget. (It's not the same as project path)"

    is_debug_mode_questions = "Run debug mode through SSH? If `no`, the following instructions will help you to create a run-files command and execute it."

    is_process_all_files_questions = "Do you want to process all files in the data bucket that is defined in config.yaml?"

    input_the_first_n_files_questions = "How many files would you like to process? \n Input a postive integer number. It processes first 'n'( n as input) number files."

    input_number_of_generated_instances_questions = "How many instances would you like to generate to run this application in parallel? \n Input a positive integer: "

    input_project_folder_questions = (
        "Enter project folder (Hit `Enter` button to use default path"
    )

    is_cleanup_resources_after_completion = "Do you want to delete all created resources? \n If you type 'no', there will be an operating cost generated from an EKS cluster (You pay $0.10 per hour for each Amazon EKS cluster you create. Sept,2022). The ec2 bastion will be stopped (no operating cost). \n However, if you type 'yes', the generated EC2 bastions and the EKS cluster will be deleted (No operating cost from ec2 and EKS cluster).\n It takes about 10~20 mins to generate a new EKS cluster."

    select_an_action = "Please select an action."

    select_an_created_resources = "Please select the created resources config folder."

    is_upload_folder_question = "Do you want to update(upload) the project folder?"

    is_changing_default_aws_setting = "Do you want to change the default AWS and EKS settings in the /mainmenu/config/ec2/config-ec2.yaml and /mainmenu/config/eks/cluster.yaml?"

    is_update_numbder_of_nodes = "The instance type you have selected has limited resources. Please generate more nodes(instances) to avoid system error !!"
