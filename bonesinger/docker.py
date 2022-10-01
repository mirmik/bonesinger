import subprocess
import time
import fcntl
import sys
import os
import tempfile
from .log import Logger

logger = Logger.instance()


def start_docker_container(image, cmd):
    print(f"Starting docker container {image}")
    random_name = f"{time.time()}"
    cmd = f"docker run -it -d --name {random_name} {image} {cmd}"
    subprocess.run(cmd, shell=True)
    return random_name


def exec_in_docker_container(container_name, cmd):
    cmd = f"docker exec {container_name} {cmd}"

    # execute and get output from command
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.stdout.read().decode("utf-8").strip()

    return output


def stop_docker_container(container_name):
    cmd = f"docker stop {container_name}"
    subprocess.run(cmd, shell=True)

    cmd = f"docker rm {container_name}"
    subprocess.run(cmd, shell=True)


def upload_file_to_docker_container(container_name, file_path, dest_path):
    cmd = f"docker cp {file_path} {container_name}:{dest_path}"
    subprocess.run(cmd, shell=True)


def make_docker_image(content, name):
    # create temporary Dockerfile
    temporary_dockerfile = tempfile.NamedTemporaryFile(mode="w", delete=False)
    temporary_dockerfile.write(content)
    temporary_dockerfile.close()

    logger.print(f"Build docker image '{name}' from Dockerfile: " + temporary_dockerfile.name)

    cmd = f"docker build -t {name} -f {temporary_dockerfile.name} ."
    proc = subprocess.Popen(cmd, shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)

    # set non-blocking output
    fcntl.fcntl(proc.stdout, fcntl.F_SETFL, fcntl.fcntl(
        proc.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)


#    output = ""
    while True:
        # read stdout
        try:
            line = proc.stdout.read()
            if line:
                print(line.decode("utf-8").strip())
        #        output += line.decode("utf-8")
        except Exception as e:
            logger.print(e)
            pass

        sys.stdout.flush()

        # check if process is finished
        if proc.poll() is not None:
            break

        # sleep for 0.1 second
        time.sleep(0.1)
