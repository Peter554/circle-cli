import logging
import shutil
from pathlib import Path
from typing import Annotated

import cyclopts
from rich.console import Console
from rich.prompt import Confirm
from rich.traceback import install as install_rich_traceback

from . import (
    api,
    api_types,
    cache,
    cache_manager,
    config,
    flags,
    output,
    service,
)

error_console = Console(stderr=True)
install_rich_traceback(console=error_console)

app = cyclopts.App(
    name="circle",
    help="CircleCI CLI for viewing pipelines, workflows and jobs",
    error_console=error_console,
)

app.register_install_completion_command()

pipelines_app = cyclopts.App(name="pipelines")
app.command(pipelines_app, alias=["pipeline", "p"])

workflows_app = cyclopts.App(name="workflows")
app.command(workflows_app, alias=["workflow", "w"])

jobs_app = cyclopts.App(name="jobs")
app.command(jobs_app, alias=["job", "j"])

cache_app = cyclopts.App(name="cache", help="Manage the local cache")
app.command(cache_app)


@app.default
@pipelines_app.default
@pipelines_app.command(name="list")
async def pipelines_list(
    *,
    branch: Annotated[
        str,
        cyclopts.Parameter(
            name=["--branch", "-b"],
            help="The branch. Defaults to the currently checked out branch. The special value @any can be used to show your pipelines for any branch.",
        ),
    ] = service.CURRENT_BRANCH,
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
    out = output.get_output(common_flags.output_format)
    out.print_pipelines(pipelines)


@pipelines_app.command(name="details", alias=["detail"])
async def pipeline_details(
    pipeline_id_or_number: Annotated[
        str,
        cyclopts.Parameter(
            help="The pipeline ID or pipeline number",
        ),
    ],
    *,
    common_flags: flags.CommonFlags = flags.CommonFlags(),
) -> None:
    """Show pipeline details"""
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    result = await app_service.get_pipeline(pipeline_id_or_number)
    out = output.get_output(common_flags.output_format)
    out.print_pipeline_detail(result)


@workflows_app.default
@workflows_app.command(name="list")
async def workflows_list(
    *,
    pipeline_id_or_number: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--pipeline", "-p"],
            help="The pipeline ID or number. Defaults to the latest pipeline for the currently checked out branch.",
        ),
    ] = None,
    common_flags: flags.CommonFlags = flags.CommonFlags(),
) -> None:
    """Show workflows for a pipeline"""
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    workflows_with_jobs = await app_service.get_workflow_jobs(
        pipeline_id_or_number, None
    )
    out = output.get_output(common_flags.output_format)
    out.print_workflows(workflows_with_jobs)


@workflows_app.command(name="failed-tests")
async def workflows_failed_tests(
    workflow_id: Annotated[
        str,
        cyclopts.Parameter(
            help="The workflow ID",
        ),
    ],
    *,
    unique: Annotated[
        output.UniqueLevel | None,
        cyclopts.Parameter(
            name=["--unique", "-u"],
            help="Show unique files or classnames instead of individual tests.",
        ),
    ] = None,
    common_flags: flags.CommonFlags = flags.CommonFlags(),
) -> None:
    """Show unique failed tests across all jobs in a workflow"""
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    result = await app_service.get_workflow_failed_tests(workflow_id)
    out = output.get_output(common_flags.output_format)
    out.print_workflow_failed_tests(result, unique)


@jobs_app.default
@jobs_app.command(name="list")
async def jobs_list(
    *,
    pipeline_id_or_number: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--pipeline", "-p"],
            help="The pipeline ID or number. Defaults to the latest pipeline for the currently checked out branch.",
        ),
    ] = None,
    workflow_ids: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name=["--workflow", "-w"],
            help="Workflow ID(s) to get jobs for. Can be specified multiple times.",
            negative=(),
        ),
    ] = None,
    statuses: Annotated[
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
    jobs = await app_service.get_workflow_jobs(
        pipeline_id_or_number, workflow_ids, set(statuses) if statuses else None
    )
    out = output.get_output(common_flags.output_format)
    out.print_jobs(jobs)


@jobs_app.command(name="details", alias=["detail"])
async def job_details(
    job_number: Annotated[
        int,
        cyclopts.Parameter(
            help="The job number",
        ),
    ],
    *,
    step_statuses: Annotated[
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
        job_number, set(step_statuses) if step_statuses else None
    )
    out = output.get_output(common_flags.output_format)
    out.print_job_details(job_details)


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
    parallel_index: Annotated[
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
    job_output = await app_service.get_job_output(job_number, step, parallel_index)
    out = output.get_output(common_flags.output_format)
    out.print_job_output(job_output, try_extract_summary)


@jobs_app.command(name="tests")
async def job_tests(
    job_number: Annotated[
        int,
        cyclopts.Parameter(
            help="The job number",
        ),
    ],
    *,
    statuses: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name=["--status", "-s"],
            help="Filter tests by result status (success, failure/failed, skipped). Can be specified multiple times.",
            negative=(),
        ),
    ] = None,
    file: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--file", "-f"],
            help="Filter tests by file path suffix.",
        ),
    ] = None,
    include_messages: Annotated[
        bool,
        cyclopts.Parameter(
            name=["--include-messages", "-m"],
            help="Include failure messages.",
            negative=(),
        ),
    ] = False,
    common_flags: flags.CommonFlags = flags.CommonFlags(),
) -> None:
    """Show test metadata for a job"""
    _setup_logging(common_flags.log_level)
    app_service = _get_app_service(common_flags)
    parsed_statuses = _parse_test_statuses(statuses) if statuses else None
    tests = await app_service.get_job_tests(job_number, parsed_statuses, file)
    out = output.get_output(common_flags.output_format)
    out.print_job_tests(tests, include_messages)


def _parse_test_statuses(statuses: list[str]) -> set[api_types.JobTestResult]:
    result = set()
    for s in statuses:
        if s == "failed":
            result.add(api_types.JobTestResult.failure)
        else:
            result.add(api_types.JobTestResult(s))
    return result


@cache_app.command(name="size")
def cache_size(
    *,
    project_slug_flags: flags.ProjectSlugFlags = flags.ProjectSlugFlags(),
    log_level: flags.LogLevelFlag = flags.DEFAULT_LOG_LEVEL,
) -> None:
    """Show total cache size"""
    _setup_logging(log_level)
    project_slug = config.get_project_slug(project_slug_flags).project_slug
    cache_ = cache.DiskcacheCache(project_slug)
    size_bytes = cache_.size()
    console = Console()
    if size_bytes < 1024:
        console.print(f"{size_bytes} B")
    elif size_bytes < 1024 * 1024:
        console.print(f"{size_bytes / 1024:.1f} KB")
    else:
        console.print(f"{size_bytes / (1024 * 1024):.1f} MB")


@cache_app.command(name="prune")
def cache_prune(
    *,
    project_slug_flags: flags.ProjectSlugFlags = flags.ProjectSlugFlags(),
    log_level: flags.LogLevelFlag = flags.DEFAULT_LOG_LEVEL,
) -> None:
    """Proactively remove expired items (expired items are also cleared on access)"""
    _setup_logging(log_level)
    project_slug = config.get_project_slug(project_slug_flags).project_slug
    cache_ = cache.DiskcacheCache(project_slug)
    cache_.prune()
    Console().print("Pruned expired cache entries")


@cache_app.command(name="clear")
def cache_clear(
    *,
    project_slug_flags: flags.ProjectSlugFlags = flags.ProjectSlugFlags(),
    log_level: flags.LogLevelFlag = flags.DEFAULT_LOG_LEVEL,
) -> None:
    """Clear all items from the cache"""
    _setup_logging(log_level)
    project_slug = config.get_project_slug(project_slug_flags).project_slug
    cache_ = cache.DiskcacheCache(project_slug)
    cache_.clear()
    Console().print("Cache cleared")


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
    token = config.get_token(common_flags.token)
    project_slug = config.get_project_slug(common_flags).project_slug
    api_client = api.APIClient(token)
    if common_flags.no_cache:
        cache_ = cache.NullCache()
    else:
        cache_ = cache.DiskcacheCache(project_slug)
    cache_manager_ = cache_manager.CacheManager(cache_)
    return service.AppService(project_slug, api_client, cache_manager_)


def main() -> None:
    app()
