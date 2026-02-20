import enum
from typing import Protocol

from .. import service


class OutputFormat(enum.StrEnum):
    pretty = "pretty"


class Output(Protocol):
    def print_pipelines(
        self, pipelines: list[service.PipelineWithWorkflows]
    ) -> None: ...

    def print_pipeline_detail(
        self, pipeline_with_workflows: service.PipelineWithWorkflows
    ) -> None: ...

    def print_workflows(
        self, workflows_with_jobs: list[service.WorkflowWithJobs]
    ) -> None: ...

    def print_jobs(self, jobs: list[service.WorkflowWithJobs]) -> None: ...

    def print_job_details(self, job_details: service.JobDetailsWithSteps) -> None: ...

    def print_job_tests(
        self,
        tests: list[service.JobTestMetadata],
        include_messages: bool,
    ) -> None: ...

    def print_job_output(
        self,
        job_output: service.JobOutput,
        try_extract_summary: bool,
    ) -> None: ...


def get_output(output_format: OutputFormat) -> Output:
    from ._pretty import PrettyOutput

    return PrettyOutput()
