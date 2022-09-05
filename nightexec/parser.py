#!/usr/bin/env python3

import yaml
import subprocess
import time
import fcntl
import os
import sys
import json

# declaringa a class


class obj:

    # constructor
    def __init__(self, dict1):
        self.__dict__.update(dict1)


def dict2obj(dict1):

    # using json.loads method and passing json.dumps
    # method and custom object hook as arguments
    return json.loads(json.dumps(dict1), object_hook=obj)


class Function:
    def __init__(self, name, run):
        self.name = name
        self.run_lines = run.split("\n")

    def compile_text(self):
        text = "\n".join(self.run_lines)
        res = f"""function {self.name}() {{
            {text}
        }}"""
        return res


class Task:
    def __init__(self, name, run):
        self.name = name
        self.run_lines = run.split("\n")

    def __str__(self):
        return f"Task({self.name})"

    def execute(self, pipeline_name, functions, executor, matrix, prefix):
        print(
            f"###PIPELINE: {pipeline_name} STEP: {self.name} matrix: {matrix}")

        matrix = dict2obj(matrix)

        # gererate random name for temporary file
        tmp_file = f"/tmp/{pipeline_name}_{self.name}_{time.time()}.tmp"

        with open(tmp_file, "w") as f:
            f.write("#!{script_executor}\n")
            f.write("set -ex\n")
            f.write(prefix)
            for function in functions:
                f.write(function.compile_text())
                f.write("\n")
            try:
                f.write("\n".join(self.run_lines).format(matrix=matrix))
            except Exception as e:
                print(e)

        executor.upload_temporary_file(tmp_file)

        # run tmp/script.sh and listen stdout and stderr
        proc = subprocess.Popen(executor.run_script_cmd(tmp_file), shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # set non-blocking output
        fcntl.fcntl(proc.stdout, fcntl.F_SETFL, fcntl.fcntl(
            proc.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(proc.stderr, fcntl.F_SETFL, fcntl.fcntl(
            proc.stderr, fcntl.F_GETFL) | os.O_NONBLOCK)

        while True:
            # read stdout
            try:
                line = proc.stdout.read()
                if line:
                    print(line.decode("utf-8").strip())
            except Exception as e:
                print(e)
                pass

            # read stderr
            try:
                line = proc.stderr.read()
                if line:
                    print(line.decode("utf-8").strip())
            except Exception as e:
                print(e)
                pass

            sys.stdout.flush()

            # check if process is finished
            if proc.poll() is not None:
                break

            # sleep for 0.1 second
            time.sleep(0.1)

        # print exit code
        print(f"Exit code: {proc.returncode}")
        if proc.returncode != 0:
            raise Exception(f"Exit code: {proc.returncode}")


def parse_yaml(file):
    with open(file, 'r') as stream:
        try:
            # create loader
            loader = yaml.Loader(stream)
            return loader.get_data()
        except yaml.YAMLError as exc:
            print(exc)
            return None


def make_tasks(yaml_data):
    tasks = []
    for task in yaml_data:
        tasks.append(Task(task["name"], task["run"]))
    return tasks


def make_functions(yaml_data):
    functions = []
    for function in yaml_data:
        functions.append(Function(function["name"], function["run"]))
    return functions


def make_prefix(yaml_data):
    return yaml_data
