from .docker import (
    start_docker_container,
    exec_in_docker_container,
    stop_docker_container,
    upload_file_to_docker_container)
import abc
import time
import subprocess
import fcntl
import sys
import os
from .util import strong_key_format, generate_random_string
from .log import Logger

logger = Logger.instance()


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

    @abc.abstractmethod
    def finish_executor(self):
        pass

    @abc.abstractmethod
    def chdir(self, path):
        pass

    @abc.abstractmethod
    def create_directory(self, path):
        pass

    def make_temporary_directory(self):
        random_name = generate_random_string(10)
        path = "/tmp/" + random_name
        self.create_directory(path)
        return path

    @abc.abstractmethod
    def clone_repository(self, url, name, basepath, branch=None):
        pass

    def execute_script(self,
                       script_lines,
                       pipeline_name,
                       script_name,
                       subst_dict,
                       prefix,
                       debug):
        logger.print(
            f"###PIPELINE: {pipeline_name}, STEP: {script_name}, VARIABLES: {subst_dict}")

        if debug:
            logger.print("###DEBUG: " + str(prefix))
            logger.print("###DEBUG: " + str(script_lines))

        # gererate random name for temporary file
        tmp_file = f"/tmp/{pipeline_name}_{script_name}_{time.time()}.tmp"

        text = f"#!{self.script_executor}\n"
        text += "set -ex\n"
        text += strong_key_format(prefix, subst_dict)

        for line in script_lines:
            line = strong_key_format(line, subst_dict)
            text += line + "\n"

        if debug:
            logger.print("Script:")
            logger.print(text)

        with open(tmp_file, "w") as f:
            f.write(text)

        self.upload_temporary_file(tmp_file)

        # run tmp/script.sh and listen stdout and stderr
        proc = subprocess.Popen(self.run_script_cmd(tmp_file), shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # set non-blocking output
        fcntl.fcntl(proc.stdout, fcntl.F_SETFL, fcntl.fcntl(
            proc.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)

        output = ""
        while True:
            # read stdout
            try:
                line = proc.stdout.read()
                if line:
                    logger.print(line.decode("utf-8").strip())
                    output += line.decode("utf-8")
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
        logger.print(f"Exit code: {proc.returncode}")
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

    def chdir(self, path):
        os.chdir(path)

    def create_directory(self, path):
        os.mkdir(path)

    def clone_repository(self, url, name, basepath, branch=None):
        if branch:
            cmd = f"git clone {url} {basepath}/{name} -b {branch} --recursive"
        else:
            cmd = f"git clone {url} {basepath}/{name} --recursive"
        subprocess.run(cmd, shell=True)

        # get commit hash to commit variable
        proc = subprocess.Popen(["git", "rev-parse", "HEAD"], cwd=name, stdout=subprocess.PIPE)
        commit = proc.stdout.read().decode("utf-8").strip()

        # get message to message variable
        proc = subprocess.Popen(["git", "log", "-1", "--pretty=%B"], cwd=name, stdout=subprocess.PIPE)
        message = proc.stdout.read().decode("utf-8").strip()

        return {"commit": commit, "message": message}

    def finish_executor(self):
        pass


class DockerExecutor(StepExecutor):
    def __init__(self, image, script_executor, addfiles=[]):
        self.image = image
        self.container_name = None
        self.init_executor(script_executor, addfiles)
        self.current_directory = None

    def init_executor(self, script_executor, addfiles):
        self.script_executor = script_executor
        self.container_name = start_docker_container(self.image, script_executor)

        for addfile in addfiles:
            upload_file_to_docker_container(self.container_name, addfile["src"], addfile["dst"])

    def run_script_cmd(self, file_path):
        if self.current_directory:
            cmd = f"docker exec -w {self.current_directory} {self.container_name} {self.script_executor} {file_path}"
        else:
            cmd = f"docker exec {self.container_name} {self.script_executor} {file_path}"
        return cmd

    def upload_temporary_file(self, path):
        upload_file_to_docker_container(self.container_name, path, path)

    def chdir(self, path):
        self.current_directory = path

    def create_directory(self, path):
        logger.print("DockerExecutor.create_directory: " + path)
        exec_in_docker_container(self.container_name, f"mkdir -p {path}")

    def clone_repository(self, url, name, basepath, branch=None):
        if branch:
            cmd = f"git clone {url} {basepath}/{name} -b {branch} --recursive"
        else:
            cmd = f"git clone {url} {basepath}/{name} --recursive"
        out = exec_in_docker_container(self.container_name, cmd)
        logger.print("Clone output:", out)

        # get commit hash to commit variable
        commit = exec_in_docker_container(self.container_name, f"git -C {basepath}/{name} rev-parse HEAD")

        # get message to message variable
        message = exec_in_docker_container(self.container_name, f"git -C {basepath}/{name} log -1 --pretty=%B")

        return {"commit": commit, "message": message}

    def finish_executor(self):
        stop_docker_container(self.container_name)
