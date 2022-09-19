import subprocess
import time


def start_docker_container(image, cmd):
    print(f"Starting docker container {image}")
    random_name = f"{time.time()}"
    cmd = f"docker run -it -d --name {random_name} {image} {cmd}"
    subprocess.run(cmd, shell=True)
    return random_name


def exec_in_docker_container(container_name, cmd):
    cmd = f"docker exec {container_name} {cmd}"
    subprocess.run(cmd, shell=True)


def upload_file_to_docker_container(container_name, file_path, dest_path):
    cmd = f"docker cp {file_path} {container_name}:{dest_path}"
    subprocess.run(cmd, shell=True)
