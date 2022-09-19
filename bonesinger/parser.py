import yaml


def parse_yaml(file):
    with open(file, 'r') as stream:
        try:
            # create loader
            loader = yaml.Loader(stream)
            return loader.get_data()
        except yaml.YAMLError as exc:
            raise exc


def make_prefix(yaml_data):
    return yaml_data
