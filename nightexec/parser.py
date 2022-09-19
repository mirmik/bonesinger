#!/usr/bin/env python3

import yaml
import subprocess
import time
import fcntl
import os
import sys
import json


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
