from bonesinger.util import strong_key_format
from .step import Step
from .util import merge_dicts
import os
import tempfile
from git import Repo
from .log import Logger
import asyncio

logger = Logger.instance()

class PipelineTimeoutException(Exception):
    pass

class Pipeline:
    def __init__(self,
                 core,
                 name: str,
                 step_records: list,
                 success_info: str,
                 workspace: str,
                 gitdata: dict,
                 watchdog : int):
        self.name = name
        self.core = core
        self.steps = self.parse_steps(step_records, core)
        self.pipeline_subst = {"pipeline_name": name}
        self.success_info_template = success_info
        self.success_info = ""
        self.workspace = workspace
        self.gitdata = gitdata
        self.watchdog = watchdog

    def parse_steps(self, step_records, core):
        return [Step.from_record(record, pipeline=self, core=core) for record in step_records]

    @staticmethod
    def from_record(record, core):
        name = record["name"]
        success_info = record.get("success_info", None)
        workspace = record.get("workspace", None)
        watchdog = record.get("watchdog", None)

        gitdata = None
        if workspace is None:
            print("Create workspace of current pipeline")
            workspace = core.executor.make_temporary_directory()

        if "git" in record:
            git = record["git"]
            giturl = git["url"]
            gitbranch = git.get("branch", "master")
            gitcommit = git.get("commit", None)
            gitname = git.get("name", None)
            gitdata = {"url": giturl, "branch": gitbranch,
                       "commit": gitcommit, "name": gitname}
            if success_info is None:
                success_info = ("Pipeline {{pipeline_name}} has been successfully executed.\n" +
                                "Commit hash: {{commit_hash}}\n" +
                                "Commit message: {{commit_message}}\n")
            #workspace = os.path.join(workspace, name)

        if "use_template" in record:
            template_name = record["use_template"]
            template = core.find_pipeline_template(template_name)
            subst = {}
            for key in record["args"]:
                subst[key] = record["args"][key]
            return Pipeline.from_record(
                core.compile_pipeline_record(template=template,
                                             subst=subst,
                                             name=name), core=core)
        else:
            return Pipeline(
                core=core,
                name=name,
                step_records=record["steps"],
                success_info=success_info,
                workspace=workspace,
                gitdata=gitdata,
                watchdog=watchdog)

    async def execute(self, executor, matrix_value, prefix, subst):
        self.core.executor.chdir(self.workspace)

        # clone repository if pipeline has git section
        if self.gitdata:
            url = self.gitdata["url"]
            name = self.gitdata["name"]
            branch = self.gitdata.get("branch", None)
            logger.print(self.gitdata)
            logger.print(f"Clone repository: {url} {name}")
            info = self.core.executor.clone_repository(url, name, basepath=self.workspace, branch=branch)
            self.workspace = os.path.join(self.workspace, name)
            self.core.executor.chdir(self.workspace)
            self.pipeline_subst["commit_hash"] = info["commit"]
            self.pipeline_subst["commit_message"] = info["message"]

        if self.core.is_debug_mode():
            logger.print("Executing pipeline " + self.name)
            for step in self.steps:
                logger.print("  " + str(step))
        
        task = asyncio.create_task(self.execute_do(executor=executor,
                         matrix_value=matrix_value,
                         prefix=prefix,
                         subst=subst))

        try:
            await asyncio.wait_for(task, self.watchdog)
        except asyncio.TimeoutError:
            logger.print("Pipeline execution has been timed out")
            raise PipelineTimeoutException()

        if self.success_info_template is not None:
            self.success_info = strong_key_format(self.success_info_template,
                                                  merge_dicts(self.pipeline_subst,
                                                              matrix_value,
                                                              {"success_info": self.success_info}))
            if self.core.is_debug_mode():
                logger.print(f"Success info: {self.success_info}")

    def set_variable(self, variable_name, variable_value):
        self.pipeline_subst[variable_name] = variable_value

    async def execute_do(self, executor, matrix_value, prefix, subst):
        for step in self.steps:
            if self.core.is_debug_mode():
                logger.print(
                    f"Execute step {step.name} for matrix value: {matrix_value}")
            try:
                logger.print("Chdir to workspace of current pipeline: " + self.workspace)
                self.core.executor.chdir(self.workspace)
                await step.execute(pipeline_name=self.name,
                             executor=executor,
                             matrix=matrix_value,
                             prefix=prefix,
                             subst=merge_dicts(self.pipeline_subst, subst))
            except Exception as e:
                logger.print(f"Error in step {step.name}: {e}")
                raise e