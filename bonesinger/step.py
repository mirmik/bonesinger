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
    def __init__(self,
                 core,
                 name: str,
                 pipeline_name: str,
                 pipeline,
                 success_info_action: str = None):
        self.core = core
        self.name = name
        self.pipeline_name = pipeline_name
        self.pipeline = pipeline
        self.success_info_action = success_info_action

    def execute(self, pipeline_name, executor: StepExecutor, matrix, prefix, subst: dict = {}):
        if self.core.is_debug_mode():
            print("Execute PipelineStep: " + self.name)

        pipeline = self.core.find_pipeline(self.pipeline_name)
        pipeline.execute(executor=executor,
                         matrix_value=matrix,
                         prefix=prefix)

        if self.success_info_action == "append":
            self.pipeline.success_info += pipeline.success_info + "\n"


class SetVariableStep(Step):
    def __init__(self,
                 core,
                 name: str,
                 variable_name: str,
                 pipeline,
                 run_lines: list = None):
        self.core = core
        self.name = name
        self.variable_name = variable_name
        self.pipeline = pipeline
        self.run_lines = run_lines

    def execute(self, pipeline_name, executor: StepExecutor, matrix, prefix, subst: dict = {}):
        if self.core.is_debug_mode():
            print("Execute SetVariableStep: " + self.name)
        output = executor.execute_script(
            script_lines=self.run_lines,
            pipeline_name=pipeline_name,
            subst_dict=subst | matrix,
            prefix=prefix,
            script_name=self.name,
            debug=self.core.is_debug_mode())

        self.pipeline.set_variable(self.variable_name, output.strip())


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
        if self.core.is_debug_mode():
            print("Execute RunStep: " + self.name)
        executor.execute_script(
            script_lines=self.run_lines,
            pipeline_name=pipeline_name,
            subst_dict=subst | matrix,
            prefix=prefix,
            script_name=self.name,
            debug=self.core.is_debug_mode())
