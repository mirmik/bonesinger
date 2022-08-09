from .docker import (
    start_docker_container,
    exec_in_docker_container,
    upload_file_to_docker_container)
import os
import time
import subprocess


class NativeExecutor:
    def __init__(self, script_executor):
        self.init_executor(script_executor)

    def init_executor(self, script_executor):
        self.script_executor = script_executor

    def run_script_cmd(self, file_path):
        cmd = f"{self.script_executor} {file_path}"
        return cmd

    def upload_temporary_file(self, path):
        pass


class DockerExecutor:
    def __init__(self, image_script, script_executor):
        self.image_script = image_script
        self.container_name = None
        self.init_executor(script_executor)

    def init_executor(self, script_executor):
        self.script_executor = script_executor

        # create temporary docker file
        tmp_docker_file = f"/tmp/{time.time()}.docker.tmp"
        with open(tmp_docker_file, "w") as f:
            f.write(self.image_script)

        # generate random image name
        self.image = f"image-{time.time()}"

        # build docker image
        cmd = f"docker build . -t {self.image} -f {tmp_docker_file}"
        subprocess.run(cmd, shell=True)

        self.container_name = start_docker_container(self.image, script_executor)

    def run_script_cmd(self, file_path):
        cmd = f"docker exec {self.container_name} {self.script_executor} {file_path}"
        return cmd

    def upload_temporary_file(self, path):
        upload_file_to_docker_container(self.container_name, path, path)
