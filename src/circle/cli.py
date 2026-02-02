import logging
import shutil
from pathlib import Path
from typing import Annotated

import cyclopts
from rich.console import Console
from rich.prompt import Confirm

from . import api, api_types, cache, cache_manager, config, flags, output, service

app = cyclopts.App(
    name="circle", help="CircleCI CLI for viewing pipelines, workflows and jobs"
)

pipelines_app = cyclopts.App(name="pipelines")
app.command(pipelines_app, alias=["pipeline", "p"])

workflows_app = cyclopts.App(name="workflows")
app.command(workflows_app, alias=["workflow", "w"])

jobs_app = cyclopts.App(name="jobs")
app.command(jobs_app, alias=["job", "j"])


@app.default
@pipelines_app.default
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
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    pipelines = await app_service.get_latest_pipelines(branch, n)
    output.print_pipelines(pipelines, common_flags.output_format)


@workflows_app.default
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
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    workflows = await app_service.get_pipeline_workflows(pipeline)
    output.print_workflows(workflows, common_flags.output_format)


@jobs_app.default
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
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    jobs = await app_service.get_jobs(
        pipeline, workflow, set(status) if status else None
    )
    output.print_jobs(jobs, common_flags.output_format)


@jobs_app.command(name="details", alias=["detail"])
async def job_details(
    job_number: Annotated[
        int,
        cyclopts.Parameter(
            help="The job number",
        ),
    ],
    *,
    step_status: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name=["--step-status", "-s"],
            help="Filter steps by status. Can be specified multiple times.",
            negative=(),
        ),
    ] = None,
    common_flags: flags.CommonFlags = flags.CommonFlags(),
) -> None:
    """Show job details"""
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    job_details = await app_service.get_job_details(
        job_number, set(step_status) if step_status else None
    )
    output.print_job_details(job_details, common_flags.output_format)


@jobs_app.command(name="output")
async def job_output(
    job_number: Annotated[
        int,
        cyclopts.Parameter(
            help="The job number",
        ),
    ],
    *,
    step: Annotated[
        # TODO Make optional? Default to first failed step?
        int,
        cyclopts.Parameter(
            name=["--step"],
            help="The step number",
        ),
    ],
    action_index: Annotated[
        int | None,
        cyclopts.Parameter(
            name=["--parallel-index"],
            help="The parallel run index. Required if there are multiple parallel runs",
        ),
    ] = None,
    try_extract_summary: Annotated[
        bool,
        cyclopts.Parameter(
            name=["--try-extract-summary"],
            help="Try to extract a summary from the output",
            negative=(),
        ),
    ] = False,
    common_flags: flags.CommonFlags = flags.CommonFlags(),
) -> None:
    """Show job output"""
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    job_output = await app_service.get_job_output(job_number, step, action_index)
    output.print_job_output(job_output, common_flags.output_format, try_extract_summary)


@app.command(name="install-claude-skill")
def install_claude_skill(
    *,
    skills_dir: Annotated[
        Path,
        cyclopts.Parameter(
            name=["--skills-dir", "-d"],
            help="The directory where Claude skills are stored",
        ),
    ] = Path.home() / ".claude" / "skills",
) -> None:
    """Install the circle-cli Claude skill"""
    console = Console()
    skill_name = "circle-cli"
    target_dir = skills_dir / skill_name
    target_file = target_dir / "SKILL.md"

    # Find the source skill file (relative to this package)
    source_file = Path(__file__).parent / "claude_skill" / "SKILL.md"
    if not source_file.exists():
        console.print(f"[red]Error:[/red] Skill file not found at {source_file}")
        raise SystemExit(1)

    # Check if skill already exists
    if target_file.exists():
        if not Confirm.ask(
            f"Skill already exists at [cyan]{target_file}[/cyan]. Overwrite?"
        ):
            console.print("Installation cancelled.")
            return

    # Create target directory and copy skill
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(source_file, target_file)
    console.print(f"[green]Installed skill to[/green] {target_file}")


def _setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=log_level.upper(),
        format="%(levelname)s [%(name)s] %(message)s",
    )


def _get_app_service(common_flags: flags.CommonFlags) -> service.AppService:
    app_config = config.load_config(common_flags)
    api_client = api.APIClient(app_config.token)
    if common_flags.no_cache:
        cache_ = cache.NullCache()
    else:
        cache_ = cache.DiskcacheCache(app_config.project_slug)
    cache_manager_ = cache_manager.CacheManager(cache_)
    return service.AppService(app_config, api_client, cache_manager_)


def main() -> None:
    app()
