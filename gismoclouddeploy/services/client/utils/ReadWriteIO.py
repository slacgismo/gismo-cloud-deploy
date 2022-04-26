
import yaml

def write_yaml(filename):
    try:
        with io.open(filename, 'w', encoding='utf8') as outfile:
            yaml.dump(data, outfile, default_flow_style=False, allow_unicode=True)
            print(f"write {filename}")
            return True
    except IOError as e:
        print ("I/O error({0}): {1}".format(e.errno, e.strerror))
    except: #handle other exceptions such as attribute errors
        print ("Unexpected error:", sys.exc_info()[0])

# Read YAML file
def read_yaml(filename):
    try:
        with open(filename, 'r') as stream:
            data_loaded = yaml.safe_load(stream)
            print(f"read {filename}")
            return data_loaded
    except IOError as e:
        print ("I/O error({0}): {1}".format(e.errno, e.strerror))
