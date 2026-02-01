from typing import Annotated

import cyclopts

from . import api, config, output, service

app = cyclopts.App(
    name="circle", help="CircleCI CLI for viewing pipelines, workflows and jobs"
)

pipelines_app = cyclopts.App(name="pipelines")
app.command(pipelines_app)

workflows_app = cyclopts.App(name="workflows")
app.command(workflows_app)

jobs_app = cyclopts.App(name="jobs")
app.command(jobs_app)


@pipelines_app.command(name="list")
async def pipelines_list(
    *,
    branch: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--branch"],
            help="The branch. Defaults to the currently checked out branch.",
        ),
    ] = None,
    config_flags: config.AppConfigFlags = config.AppConfigFlags(),
    n: Annotated[
        int,
        cyclopts.Parameter(
            name=["--number", "-n"], help="The number of pipelines to show"
        ),
    ] = 3,
) -> None:
    """Show pipelines for a branch"""
    app_service = _get_app_service(config_flags)
    pipelines = await app_service.get_pipelines(branch, n)
    output.print(pipelines)


@workflows_app.command(name="list")
async def workflows_list(
    *,
    pipeline: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--pipeline", "-p"],
            help="The pipeline ID. Defaults to the latest pipeline for the currently checked out branch.",
        ),
    ] = None,
    config_flags: config.AppConfigFlags = config.AppConfigFlags(),
) -> None:
    """Show workflows for a pipeline"""
    app_service = _get_app_service(config_flags)
    workflows = await app_service.get_workflows(pipeline)
    output.print(workflows)


@jobs_app.command(name="list")
async def jobs_list(
    *,
    pipeline: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--pipeline", "-p"],
            help="The pipeline ID. Defaults to the latest pipeline for the currently checked out branch.",
        ),
    ] = None,
    workflow: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name=["--workflow", "-w"],
            help="Workflow ID(s) to get jobs for. Can be specified multiple times.",
            negative=(),
        ),
    ] = None,
    config_flags: config.AppConfigFlags = config.AppConfigFlags(),
) -> None:
    """Show jobs for workflows"""
    app_service = _get_app_service(config_flags)
    results = await app_service.get_jobs(pipeline, workflow)
    output.print(results)


def _get_app_service(config_flags: config.AppConfigFlags) -> service.AppService:
    app_config = config.load_config(config_flags)
    api_client = api.BasicAPIClient(app_config.token)
    return service.AppService(app_config, api_client)


def main() -> None:
    app()
