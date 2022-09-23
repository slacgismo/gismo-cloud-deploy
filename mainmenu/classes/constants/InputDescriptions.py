import enum



class InputDescriptions(enum.Enum):
    is_cleanup_resources_after_completion = "create"
    input_project_name_in_tags="Enter the name of project. This will be listed in all created cloud resources, and it's used for managing budege. (It's not the same as project path)"

    is_debug_mode_questions = "Run debug mode through SSH? If `no`, an following instructions will help you to create a run-files command and execute it."
    
    is_process_all_files_questions = "Do you want to process all files in the databucket that defined in config.yaml?"

    input_the_first_n_files_questions = "How many files you would like process? \n Input an postive integer number. It processes first 'n'( n as input) number files.",

    input_number_of_generated_instances_questions = "How many instances you would like to generate to run this application in parallel? \n Input an postive integer: "

    input_project_folder_questions = "Enter project folder (Hit `Enter` button to use default path",

    select_an_action = "Select an actio!!"

    select_an_created_resources = "Select created resources config path ?"