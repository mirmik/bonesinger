from bonesinger.util import strong_key_format
from .step import RunStep, PipelineStep, SetVariableStep


class Pipeline:
    def __init__(self,
                 core,
                 name: str,
                 step_records: list,
                 watchdog: int,
                 success_info: str):
        self.name = name
        self.core = core
        self.steps = self.parse_steps(step_records)
        self.watchdog = watchdog
        self.pipeline_subst = {}
        self.success_info_template = success_info
        self.success_info = ""

    def execute(self, executor, matrix_value, prefix):
        if self.core.is_debug_mode():
            print("Executing pipeline " + self.name)
            for step in self.steps:
                print("  " + str(step))
        for step in self.steps:
            if self.core.is_debug_mode():
                print(f"Execute step {step.name} for matrix value: {matrix_value}")
            try:
                step.execute(pipeline_name=self.name,
                             executor=executor,
                             matrix=matrix_value,
                             prefix=prefix,
                             subst=self.pipeline_subst)
            except Exception as e:
                print(f"Error in step {step.name}: {e}")
                raise e

        if self.success_info_template is not None:
            self.success_info = strong_key_format(self.success_info_template,
                                                  self.pipeline_subst |
                                                  matrix_value |
                                                  {"success_info": self.success_info})
            if self.core.is_debug_mode():
                print(f"Success info: {self.success_info}")

    def parse_steps(self, list_of_step_records):
        steps = []
        for step_record in list_of_step_records:
            name = step_record["name"]
            if "run" in step_record:
                run = step_record["run"]
                steps.append(RunStep(core=self.core,
                                     name=name,
                                     run=run,
                                     pipeline=self))
            elif "run_pipeline" in step_record:
                pipeline_name = step_record["run_pipeline"]
                success_info_action = step_record.get("success_info", "ignore")
                steps.append(PipelineStep(core=self.core,
                                          name=name,
                                          pipeline_name=pipeline_name,
                                          pipeline=self,
                                          success_info_action=success_info_action))
            elif "set_variable" in step_record:
                variable_name = step_record["set_variable"]
                run_script = step_record["script"]
                steps.append(SetVariableStep(core=self.core,
                                             name=name,
                                             variable_name=variable_name,
                                             run_lines=run_script.split("\n"),
                                             pipeline=self))
            else:
                raise Exception("Invalid step record: " + str(step_record))

        return steps

    def set_variable(self, variable_name, variable_value):
        self.pipeline_subst[variable_name] = variable_value
