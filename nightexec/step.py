import fcntl
import os
import sys
import subprocess
import time
import json
from .executors import StepExecutor


class obj:

    # constructor
    def __init__(self, dict1):
        self.__dict__.update(dict1)


def dict2obj(dict1):

    # using json.loads method and passing json.dumps
    # method and custom object hook as arguments
    return json.loads(json.dumps(dict1), object_hook=obj)


class Step:
    pass


class PipelineStep(Step):
    def __init__(self, core, name: str, pipeline_name: str, pipeline):
        self.core = core
        self.name = name
        self.pipeline_name = pipeline_name
        self.pipeline = pipeline

    def execute(self, pipeline_name, executor: StepExecutor, matrix, prefix):
        pipeline = self.core.find_pipeline(self.pipeline_name)
        pipeline.execute(executor=executor,
                         matrix_value=matrix,
                         prefix=prefix)


class RunStep(Step):
    def __init__(self, core, pipeline,
                 name: str,
                 run: list):
        self.core = core
        self.pipeline = pipeline
        self.name = name
        self.run_lines = run.split("\n")

    def __str__(self):
        return f"Task({self.name})"

    def execute(self,
                pipeline_name: str,
                executor: StepExecutor,
                matrix: dict,
                prefix: str,
                subst: dict = {}):
        print(
            f"###PIPELINE: {pipeline_name} STEP: {self.name} matrix: {matrix}")

        matrix = dict2obj(matrix)

        # gererate random name for temporary file
        tmp_file = f"/tmp/{pipeline_name}_{self.name}_{time.time()}.tmp"

        with open(tmp_file, "w") as f:
            f.write("#!{script_executor}\n")
            f.write("set -ex\n")
            f.write(prefix)

            for line in self.run_lines:
                line = line.format(**subst)
                f.write(line + "\n")

        executor.upload_temporary_file(tmp_file)

        if self.core.is_debug_mode():
            print(f"###DEBUG: {self.run_lines}")
            print(prefix)

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
