from .docker import (
    start_docker_container,
    exec_in_docker_container,
    upload_file_to_docker_container)
import abc


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
