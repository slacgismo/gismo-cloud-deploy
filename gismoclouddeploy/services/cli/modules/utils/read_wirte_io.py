import yaml

# Read YAML file
def read_yaml(filename):
    try:
        with open(filename, "r") as stream:
            data_loaded = yaml.safe_load(stream)

            return data_loaded
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))
