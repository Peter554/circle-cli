"""Rich output formatting for CLI."""

import json
from datetime import datetime, timezone

import humanize
from rich.console import Console
from rich.panel import Panel

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
        if not pipelines:
            console.print("No pipelines found")
            return

        # Create panel for each pipeline
        for pipeline in sorted(pipelines, key=lambda p: p.created_at, reverse=True):
            state = _format_pipeline_state(pipeline.state)
            commit = _get_commit_subject(pipeline)
            created = _format_relative_time(pipeline.created_at)
            url = _build_pipeline_url(pipeline)
            branch = pipeline.vcs.branch if pipeline.vcs else "unknown"
            commit_hash = pipeline.vcs.revision[:12] if pipeline.vcs else "unknown"

            content = f"""[bold]ID:[/bold] {pipeline.id}
[bold]Created:[/bold] {created}
[bold]State:[/bold] {state}
[bold]Commit:[/bold] {commit_hash} {commit}
[bold]Branch:[/bold] {branch}
[bold]Link:[/bold] {url}"""

            panel = Panel(
                content,
                title=f"[bold]Pipeline {pipeline.id}[/bold]",
                border_style=_get_pipeline_border_style(pipeline.state),
            )
            console.print(panel)


def _format_pipeline_state(state: api_types.PipelineState) -> str:
    """Format pipeline state with color."""
    if state == api_types.PipelineState.errored:
        return f"[red]{state}[/red]"
    return str(state)


def _get_pipeline_border_style(state: api_types.PipelineState) -> str:
    """Get border style for pipeline panel based on state."""
    if state == api_types.PipelineState.errored:
        return "red"
    return "white"


def _get_commit_subject(pipeline: api_types.Pipeline) -> str:
    """Get commit subject."""
    if pipeline.vcs and pipeline.vcs.commit and pipeline.vcs.commit.subject:
        return pipeline.vcs.commit.subject
    return ""


def _format_relative_time(dt: datetime) -> str:
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return humanize.naturaltime(dt)


def _build_pipeline_url(pipeline: api_types.Pipeline) -> str:
    parts = pipeline.project_slug.split("/")
    assert len(parts) == 3, f"Invalid project slug: {pipeline.project_slug}"
    vcs_provider = "github" if parts[0] == "gh" else "bitbucket"
    org = parts[1]
    repo = parts[2]
    return f"https://app.circleci.com/pipelines/{vcs_provider}/{org}/{repo}/{pipeline.number}"


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
