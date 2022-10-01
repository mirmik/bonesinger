
import json
from .executors import StepExecutor
from .util import merge_dicts
from .log import Logger


class obj:

    # constructor
    def __init__(self, dict1):
        self.__dict__.update(dict1)


def dict2obj(dict1):

    # using json.loads method and passing json.dumps
    # method and custom object hook as arguments
    return json.loads(json.dumps(dict1), object_hook=obj)


class Step:
    @staticmethod
    def from_record(step_record, pipeline, core):
        name = step_record["name"]
        if "run" in step_record:
            run = step_record["run"]
            return RunStep(core=core,
                           name=name,
                           run=run,
                           pipeline=pipeline)
        elif "run_pipeline" in step_record:
            pipeline_name = step_record["run_pipeline"]
            success_info_action = step_record.get("success_info", "ignore")
            return PipelineStep(core=core,
                                name=name,
                                pipeline_name=pipeline_name,
                                pipeline=pipeline,
                                success_info_action=success_info_action)
        elif "set_variable" in step_record:
            variable_name = step_record["set_variable"]
            run_script = step_record["script"]
            return SetVariableStep(core=core,
                                   name=name,
                                   variable_name=variable_name,
                                   run_lines=run_script.split("\n"),
                                   pipeline=pipeline)
        else:
            raise Exception("Invalid step record: " + str(step_record))


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
                         prefix=prefix,
                         subst=subst)

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
            subst_dict=merge_dicts(subst, matrix),
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
            subst_dict=merge_dicts(subst, matrix),
            prefix=prefix,
            script_name=self.name,
            debug=self.core.is_debug_mode())
