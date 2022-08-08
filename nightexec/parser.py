#!/usr/bin/env python3

import yaml
import subprocess
import time
import fcntl
import os
import sys


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

    def execute(self, pipeline_name, functions):
        print(f"###PIPELINE: {pipeline_name} STEP: {self.name}")

        with open("/tmp/script.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("set -ex\n")
            for function in functions:
                f.write(function.compile_text())
                f.write("\n")
            f.write("\n".join(self.run_lines))

        # run tmp/script.sh and listen stdout and stderr
        proc = subprocess.Popen(["/bin/bash", "/tmp/script.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # set non-blocking output
        fcntl.fcntl(proc.stdout, fcntl.F_SETFL, fcntl.fcntl(proc.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(proc.stderr, fcntl.F_SETFL, fcntl.fcntl(proc.stderr, fcntl.F_GETFL) | os.O_NONBLOCK)

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
