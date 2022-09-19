from .docker import (
    start_docker_container,
    exec_in_docker_container,
    upload_file_to_docker_container)
import abc
import time
import subprocess
import fcntl
import sys
import os
from .util import strong_key_format


class StepExecutor:
    @abc.abstractmethod
    def init_executor(self, script_executor):
        pass

    @abc.abstractmethod
    def run_script_cmd(self, file_path):
        pass

    @abc.abstractmethod
    def upload_temporary_file(self, path):
        pass

    def execute_script(self,
                       script_lines,
                       pipeline_name,
                       script_name,
                       subst_dict,
                       prefix,
                       debug):
        print(
            f"###PIPELINE: {pipeline_name}, STEP: {script_name}, VARIABLES: {subst_dict}")

        if debug:
            print("###DEBUG: " + str(prefix))
            print("###DEBUG: " + str(script_lines))

        # gererate random name for temporary file
        tmp_file = f"/tmp/{pipeline_name}_{script_name}_{time.time()}.tmp"

        text = f"#!{self.script_executor}\n"
        text += "set -ex\n"
        text += strong_key_format(prefix, subst_dict)

        for line in script_lines:
            line = strong_key_format(line, subst_dict)
            text += line + "\n"

        if debug:
            print("Script:")
            print(text)

        with open(tmp_file, "w") as f:
            f.write(text)

        self.upload_temporary_file(tmp_file)

        # run tmp/script.sh and listen stdout and stderr
        proc = subprocess.Popen(self.run_script_cmd(tmp_file), shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # set non-blocking output
        fcntl.fcntl(proc.stdout, fcntl.F_SETFL, fcntl.fcntl(
            proc.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(proc.stderr, fcntl.F_SETFL, fcntl.fcntl(
            proc.stderr, fcntl.F_GETFL) | os.O_NONBLOCK)

        output = ""
        while True:
            # read stdout
            try:
                line = proc.stdout.read()
                if line:
                    print(line.decode("utf-8").strip())
                    output += line.decode("utf-8")
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
            raise Exception(f"{pipeline_name}:{script_name}: exit code: {proc.returncode}")

        return output


class NativeExecutor(StepExecutor):
    def __init__(self, script_executor):
        self.init_executor(script_executor)

    def init_executor(self, script_executor):
        self.script_executor = script_executor

    def run_script_cmd(self, file_path):
        cmd = f"{self.script_executor} {file_path}"
        return cmd

    def upload_temporary_file(self, path):
        pass


class DockerExecutor(StepExecutor):
    def __init__(self, image, script_executor, addfiles=[]):
        self.image = image
        self.container_name = None
        self.init_executor(script_executor, addfiles)

    def init_executor(self, script_executor, addfiles):
        self.script_executor = script_executor
        self.container_name = start_docker_container(self.image, script_executor)

        for addfile in addfiles:
            upload_file_to_docker_container(self.container_name, addfile["src"], addfile["dst"])

    def run_script_cmd(self, file_path):
        cmd = f"docker exec {self.container_name} {self.script_executor} {file_path}"
        return cmd

    def upload_temporary_file(self, path):
        upload_file_to_docker_container(self.container_name, path, path)
