from .step import Step, RunStep, PipelineStep


class Pipeline:
    def __init__(self, core, name: str, step_records: list, watchdog: int):
        self.name = name
        self.core = core
        self.steps = self.parse_steps(step_records)
        self.watchdog = watchdog

    def execute(self, executor, matrix_value, prefix):
        for step in self.steps:
            step.execute(pipeline_name=self.name,
                         executor=executor,
                         matrix=matrix_value,
                         prefix=prefix)

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
                steps.append(PipelineStep(core=self.core,
                                          name=name,
                                          pipeline_name=pipeline_name,
                                          pipeline=self))
            else:
                raise Exception("Invalid step record: " + str(step_record))

        return steps
