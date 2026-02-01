import logging
from typing import Annotated

import cyclopts

from . import api, api_types, cache, config, flags, output, service

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
    common_flags: flags.CommonFlags = flags.CommonFlags(),
    n: Annotated[
        int,
        cyclopts.Parameter(
            name=["--number", "-n"], help="The number of pipelines to show"
        ),
    ] = 3,
) -> None:
    """Show pipelines for a branch"""
    _setup_logging(common_flags)
    app_service = _get_app_service(common_flags)
    pipelines = await app_service.get_pipelines(branch, n)
    output.print_pipelines(pipelines, common_flags.output_format)


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
    common_flags: flags.CommonFlags = flags.CommonFlags(),
) -> None:
    """Show workflows for a pipeline"""
    _setup_logging(common_flags)
    app_service = _get_app_service(common_flags)
    workflows = await app_service.get_workflows(pipeline)
    output.print_workflows(workflows, common_flags.output_format)


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
    status: Annotated[
        list[api_types.JobStatus] | None,
        cyclopts.Parameter(
            name=["--status", "-s"],
            help="Filter jobs by status. Can be specified multiple times.",
            negative=(),
        ),
    ] = None,
    common_flags: flags.CommonFlags = flags.CommonFlags(),
) -> None:
    """Show jobs for workflows"""
    _setup_logging(common_flags)
    app_service = _get_app_service(common_flags)
    jobs = await app_service.get_jobs(
        pipeline, workflow, set(status) if status else None
    )
    output.print_jobs(jobs, common_flags.output_format)


def _setup_logging(common_flags: flags.CommonFlags) -> None:
    logging.basicConfig(
        level=common_flags.log_level.upper(),
        format="%(levelname)s [%(name)s] %(message)s",
    )


def _get_app_service(common_flags: flags.CommonFlags) -> service.AppService:
    app_config = config.load_config(common_flags)
    api_client = api.APIClient(app_config.token)
    if common_flags.no_cache:
        print("NOCACHE")
        api_cache = cache.NullCache()
    else:
        api_cache = cache.DiskcacheCache()
    return service.AppService(app_config, api_client, api_cache)


def main() -> None:
    app()
