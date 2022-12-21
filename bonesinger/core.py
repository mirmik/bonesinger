from .executors import StepExecutor
from .step import RunStep
from .pipeline import Pipeline
from .util import strong_key_format, merge_dicts
import tempfile
import os
from git import Repo
import traceback
from .log import Logger
import asyncio

logger = Logger.instance()


def matrix_iterator(matrix):
    def prod(lst):
        res = 1
        for x in lst:
            res *= x
        return res

    keys = sorted(matrix.keys())
    values_list = [matrix[key] for key in keys]
    count_of_elements = prod([len(values) for values in values_list])
    for i in range(count_of_elements):
        matrix_value = {}
        for j in range(len(keys)):
            matrix_value[keys[j]] = values_list[j][i % len(values_list[j])]
        yield matrix_value


def sanitize_url(text):
    # find url in text and replace it with "***url***"
    # to hide it from logs
    import re
    url_regex = re.compile(
        r'(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+')
    return url_regex.sub('***url***', text)


class Core:
    def __init__(self,
                 executor: StepExecutor,
                 matrix: dict,
                 prefix: str,
                 debug: bool,
                 pipeline_records: list,
                 on_success_records: dict,
                 on_failure_records: dict,
                 pipeline_template: list,
                 security_options: dict,
                 timeout: int):
        self.pipeline_template = pipeline_template
        self.executor = executor
        self.matrix = matrix
        self.prefix = prefix
        self.debug = debug
        self.pipelines = self.parse_pipelines(pipeline_records)
        self.on_success_script = self.make_task_list(on_success_records)
        self.on_failure_script = self.make_task_list(on_failure_records)
        self.security_options = security_options
        self.timeout = timeout

    def make_task_list(self, records) -> list:
        """make list of Step objects from records"""
        tasks = []
        if records is None:
            return tasks
        for record in records:
            name = record["name"]
            run = record["run"]
            tasks.append(RunStep(core=self,
                                 name=name,
                                 run=run,
                                 pipeline=None))
        return tasks

    def is_debug_mode(self):
        return self.debug

    def compile_pipeline_record(self, name, template, subst):
        def subst_value(value):
            if isinstance(value, str):
                return strong_key_format(value, subst)
            elif isinstance(value, list):
                return [subst_value(x) for x in value]
            elif isinstance(value, dict):
                return {key: subst_value(value[key]) for key in value}
            else:
                return value

        rec = subst_value(template)
        rec['name'] = name

        return rec

    def parse_pipelines(self, list_of_pipeline_records):
        pipelines = []
        for pipeline_record in list_of_pipeline_records:
            pipelines.append(Pipeline.from_record(pipeline_record, core=self))
        return pipelines

    def find_pipeline(self, name: str):
        for pipeline in self.pipelines:
            if pipeline.name == name:
                return pipeline
        raise Exception("Pipeline not found: " + name)

    def find_pipeline_template(self, name):
        for template in self.pipeline_template:
            if template["name"] == name:
                return template
        raise Exception("Pipeline template not found: " + name)

    def create_build_directory_and_change_it(self):
        logger.print("Create core workspace")
        temporary_directory = self.executor.make_temporary_directory()
        self.executor.chdir(temporary_directory)
        self.workspace = temporary_directory

    async def execute_entrypoint(self, entrypoint: str):
        self.create_build_directory_and_change_it()
        pipeline = self.find_pipeline(entrypoint)
        for matrix_value in matrix_iterator(self.matrix):
            try:
                if self.debug:
                    logger.print(
                        f"Execute pipeline {pipeline.name} for matrix value: {matrix_value}")
                
                task = asyncio.create_task(pipeline.execute(executor=self.executor,
                    matrix_value=matrix_value,
                    prefix=self.prefix,
                    subst={}))

                await asyncio.wait_for(task, timeout=self.timeout)
            except asyncio.TimeoutError:            
                current_directory = os.getcwd()
                logger.print("Timeout")
                logger.print("Location: " + current_directory)
                logger.print("Traceback: " + traceback.format_exc())
                await self.on_failure(pipeline, matrix_value, f"Global timeout exceeded ({self.timeout}s)")
                break
            except Exception as e:
                current_directory = os.getcwd()
                logger.print("Exception: " + str(e))
                logger.print("Location: " + current_directory)
                logger.print("Traceback: " + traceback.format_exc())
                await self.on_failure(pipeline, matrix_value, e)
                break

            await self.on_success(pipeline, matrix_value)

        self.executor.finish_executor()

    async def on_success(self, pipeline, matrix_value):
        if self.security_options["hide_links"]:
            pipeline.success_info = sanitize_url(pipeline.success_info)

        if self.debug:
            logger.print("Success: " + pipeline.name)
            logger.print("Matrix value: " + str(matrix_value))
            logger.print("Success info: " + str(pipeline.success_info))
        for task in self.on_success_script:
            await task.execute(pipeline_name=pipeline.name,
                         executor=self.executor,
                         matrix=matrix_value,
                         prefix=self.prefix,
                         subst={"pipeline_name": pipeline.name,
                                "success_info": pipeline.success_info,
                                **pipeline.pipeline_subst})

    async def on_failure(self, pipeline, matrix_value, exception):
        if self.security_options["hide_links"]:
            pipeline.success_info = sanitize_url(pipeline.success_info)

        error_message = str(exception)
        for task in self.on_failure_script:
            await task.execute(pipeline_name=pipeline.name,
                         executor=self.executor,
                         matrix=matrix_value,
                         prefix=self.prefix,
                         subst={"pipeline_name": pipeline.name,
                                "error_message": error_message,
                                **pipeline.pipeline_subst})
