import yaml
from .log import Logger

logger = Logger.instance()


def parse_yaml(file):
    with open(file, 'r') as stream:
        try:
            # create loader
            loader = yaml.Loader(stream)
            return loader.get_data()
        except yaml.YAMLError as exc:
            raise exc


def parse_yaml_url(url):
    if url.startswith('http'):
        import requests
        r = requests.get(url)
        logger.print(f"download content from url: {url}:\n{r.text}")
        return yaml.load(r.text)
    else:
        return parse_yaml(url)


def parse_yaml_content(content):
    loader = yaml.Loader(content)
    return loader.get_data()


def get_url_content(url):
    if url.startswith('http'):
        import requests
        r = requests.get(url)
        return r.text
    else:
        with open(url, 'r') as stream:
            return stream.read()


def make_prefix(yaml_data):
    return yaml_data
