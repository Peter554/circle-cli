"""Rich output formatting for CLI."""

import json
from typing import NoReturn

from rich.console import Console

from . import api_types, flags

console = Console()


def print(o: object) -> None:
    console.print(o)


def print_pipelines(
    pipelines: list[api_types.Pipeline], output_format: flags.OutputFormat
) -> None:
    if output_format == flags.OutputFormat.json:
        data = [p.model_dump(mode="json") for p in pipelines]
        console.print(json.dumps(data, indent=2))
    else:
        raise NotImplementedError("Pretty output not yet implemented")


def print_workflows(
    workflows: list[api_types.Workflow], output_format: flags.OutputFormat
) -> None:
    if output_format == flags.OutputFormat.json:
        data = [w.model_dump(mode="json") for w in workflows]
        console.print(json.dumps(data, indent=2))
    else:
        raise NotImplementedError("Pretty output not yet implemented")


def print_jobs(
    jobs: list[tuple[api_types.Workflow, list[api_types.Job]]],
    output_format: flags.OutputFormat,
) -> None:
    if output_format == flags.OutputFormat.json:
        data = [
            {
                "workflow": workflow.model_dump(mode="json"),
                "jobs": [job.model_dump(mode="json") for job in job_list],
            }
            for workflow, job_list in jobs
        ]
        console.print(json.dumps(data, indent=2))
    else:
        raise NotImplementedError("Pretty output not yet implemented")
