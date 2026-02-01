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
    pipelines: list[tuple[api_types.Pipeline, list[api_types.Workflow]]],
    output_format: flags.OutputFormat,
) -> None:
    if output_format == flags.OutputFormat.json:
        data = [p.model_dump(mode="json") for p, _ in pipelines]
        console.print(json.dumps(data, indent=2))
    else:
        if not pipelines:
            console.print("No pipelines found")
            return

        # Create panel for each pipeline
        for pipeline, workflows in sorted(
            pipelines, key=lambda x: x[0].created_at, reverse=True
        ):
            state = _format_pipeline_state(pipeline.state)
            commit = _get_commit_subject(pipeline)
            created = _format_relative_time(pipeline.created_at)
            url = _build_pipeline_url(pipeline)
            commit_hash = pipeline.vcs.revision[:12] if pipeline.vcs else "unknown"

            # Sort workflows by created_at
            sorted_workflows = sorted(workflows, key=lambda w: w.created_at)

            # Build workflows status line
            workflow_status = ", ".join(
                f"{w.name}: {_format_workflow_status(w.status)}"
                for w in sorted_workflows
            )

            content = f"""[bold]ID:[/bold] {pipeline.id}
[bold]Created:[/bold] {created}
[bold]State:[/bold] {state}
[bold]Commit:[/bold] {commit_hash} {commit}
[bold]Workflows:[/bold] {workflow_status}
[bold]Link:[/bold] [link={url}]{url}[/link]"""

            panel = Panel(
                content,
                title=f"[bold]Pipeline {pipeline.id}[/bold]",
                border_style=_get_pipeline_border_style(pipeline.state),
            )
            console.print(panel)


def print_workflows(
    workflows: list[api_types.Workflow], output_format: flags.OutputFormat
) -> None:
    if output_format == flags.OutputFormat.json:
        data = [w.model_dump(mode="json") for w in workflows]
        console.print(json.dumps(data, indent=2))
    else:
        if not workflows:
            console.print("No workflows found")
            return

        # Get pipeline info from first workflow
        pipeline_number = workflows[0].pipeline_number
        console.print(f"\nWorkflows for pipeline: [bold]#{pipeline_number}[/bold]\n")

        # Create panel for each workflow
        for workflow in sorted(workflows, key=lambda w: w.created_at):
            status = _format_workflow_status(workflow.status)
            duration = _format_duration(workflow.created_at, workflow.stopped_at)
            created = _format_relative_time(workflow.created_at)
            url = _build_workflow_url(workflow)

            content = f"""[bold]ID:[/bold] {workflow.id}
[bold]Created:[/bold] {created}
[bold]Status:[/bold] {status}
[bold]Duration:[/bold] {duration}
[bold]Link:[/bold] [link={url}]{url}[/link]"""

            panel = Panel(
                content,
                title=f"[bold]{workflow.name}[/bold]",
                border_style=_get_workflow_border_style(workflow.status),
            )
            console.print(panel)


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


def _format_workflow_status(status: api_types.WorkflowStatus) -> str:
    """Format workflow status with color."""
    if status == api_types.WorkflowStatus.success:
        return f"[green]{status}[/green]"
    elif status in {
        api_types.WorkflowStatus.failed,
        api_types.WorkflowStatus.error,
        api_types.WorkflowStatus.failing,
    }:
        return f"[red]{status}[/red]"
    elif status == api_types.WorkflowStatus.running:
        return f"[yellow]{status}[/yellow]"
    return str(status)


def _get_workflow_border_style(status: api_types.WorkflowStatus) -> str:
    """Get border style for workflow panel based on status."""
    if status == api_types.WorkflowStatus.success:
        return "green"
    elif status in {
        api_types.WorkflowStatus.failed,
        api_types.WorkflowStatus.error,
        api_types.WorkflowStatus.failing,
    }:
        return "red"
    elif status == api_types.WorkflowStatus.running:
        return "yellow"
    return "white"


def _format_duration(created_at: datetime, stopped_at: datetime | None) -> str:
    """Format duration between created and stopped times."""
    if stopped_at is None:
        # Still running, show elapsed time
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - created_at
        return f"{humanize.naturaldelta(delta)} (running)"

    # Completed, show total duration
    delta = stopped_at - created_at
    return humanize.naturaldelta(delta)


def _build_workflow_url(workflow: api_types.Workflow) -> str:
    """Build CircleCI workflow URL."""
    parts = workflow.project_slug.split("/")
    assert len(parts) == 3, f"Invalid project slug: {workflow.project_slug}"
    vcs_provider = "github" if parts[0] == "gh" else "bitbucket"
    org = parts[1]
    repo = parts[2]
    return f"https://app.circleci.com/pipelines/{vcs_provider}/{org}/{repo}/{workflow.pipeline_number}/workflows/{workflow.id}"
