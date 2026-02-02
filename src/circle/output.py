"""Rich output formatting for CLI."""

import json
from collections import defaultdict
from datetime import datetime, timezone

import humanize
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import api_types, flags, service

console = Console()


def print(o: object) -> None:
    console.print(o)


def print_pipelines(
    pipelines: list[tuple[api_types.Pipeline, list[api_types.Workflow]]],
    output_format: flags.OutputFormat,
) -> None:
    if output_format == flags.OutputFormat.json:
        data = [
            {
                "pipeline": pipeline.model_dump(mode="json"),
                "workflows": [w.model_dump(mode="json") for w in workflows],
            }
            for pipeline, workflows in pipelines
        ]
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
[bold]Link:[/bold] {_format_link(url)}"""

            panel = Panel(
                content,
                title=f"[bold]Pipeline {pipeline.id}[/bold]",
                border_style=_get_pipeline_border_style(pipeline.state, workflows),
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

        # Group workflows by pipeline_id
        workflows_by_pipeline: dict[str, list[api_types.Workflow]] = defaultdict(list)
        for workflow in workflows:
            workflows_by_pipeline[workflow.pipeline_id].append(workflow)

        # Display workflows grouped by pipeline
        for pipeline_id, pipeline_workflows in workflows_by_pipeline.items():
            console.print(f"\n[bold]Pipeline:[/bold] {pipeline_id}\n")

            # Create panel for each workflow, sorted by created_at
            for workflow in sorted(pipeline_workflows, key=lambda w: w.created_at):
                status = _format_workflow_status(workflow.status)
                duration = _format_duration(workflow.created_at, workflow.stopped_at)
                created = _format_relative_time(workflow.created_at)
                url = _build_workflow_url(workflow)

                content = f"""
[bold]ID:[/bold] {workflow.id}
[bold]Name:[/bold] {workflow.name}
[bold]Created:[/bold] {created}
[bold]Status:[/bold] {status}
[bold]Duration:[/bold] {duration}
[bold]Link:[/bold] {_format_link(url)}"""

                panel = Panel(
                    content,
                    title=f"[bold]{workflow.name} ({workflow.id})[/bold]",
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
        if not jobs:
            console.print("No jobs found")
            return

        # Display jobs for each workflow
        for workflow, job_list in sorted(jobs, key=lambda x: x[0].created_at):
            console.print(f"\n[bold]Workflow:[/bold] {workflow.name} ({workflow.id})\n")

            if not job_list:
                console.print("No matching jobs")
                continue

            # Sort jobs by status priority, then chronologically
            sorted_jobs = sorted(
                job_list, key=lambda j: _get_job_status_priority(j.status)
            )

            # Create table
            table = Table(show_header=True, header_style="bold")
            table.add_column("Number")
            table.add_column("Name", overflow="ellipsis", max_width=64)
            table.add_column("Status")
            table.add_column("Started")
            table.add_column("Duration")
            table.add_column("Link")

            for job in sorted_jobs:
                status = _format_job_status(job.status)
                started = (
                    _format_relative_time(job.started_at) if job.started_at else ""
                )
                duration = _format_duration(job.started_at, job.stopped_at)

                # Build link if job_number exists
                if job.job_number is not None:
                    url = _build_job_url(job)
                    link = _format_link(url)
                else:
                    link = ""

                table.add_row(
                    str(job.job_number or ""),
                    job.name,
                    status,
                    started,
                    duration,
                    link,
                )

            console.print(table)
            console.print()


def print_job_details(
    job_details: service.JobDetailsWithSteps,
    output_format: flags.OutputFormat,
) -> None:
    if output_format == flags.OutputFormat.json:
        data = {
            "details": job_details.details.model_dump(mode="json"),
            "steps_by_action_index": {
                action_index: [
                    {
                        "step_index": sa.step_index,
                        "step": sa.step.model_dump(mode="json"),
                        "action": sa.action.model_dump(mode="json"),
                    }
                    for sa in step_actions
                ]
                for action_index, step_actions in job_details.steps_by_action_index.items()
            },
        }
        console.print(json.dumps(data, indent=2))
    else:
        details = job_details.details

        # Build job summary
        status = _format_job_status(details.status)
        started = _format_relative_time(details.started_at)
        duration = _format_duration_ms(details.duration)
        url = details.web_url

        summary = f"""[bold]Number:[/bold] {details.number}
[bold]Name:[/bold] {details.name}
[bold]Status:[/bold] {status}
[bold]Started:[/bold] {started}
[bold]Duration:[/bold] {duration}
[bold]Parallelism:[/bold] {details.parallelism}
[bold]Link:[/bold] {_format_link(url)}"""

        # Build step tables
        renderables = [Text.from_markup(summary)]

        for action_index in sorted(job_details.steps_by_action_index.keys()):
            step_actions = job_details.steps_by_action_index[action_index]

            # Calculate parallel run duration
            actions = [sa.action for sa in step_actions]
            run_duration = _calculate_parallel_run_duration(actions)

            # Add spacing and header
            renderables.append(Text())
            if details.parallelism > 1:
                renderables.append(
                    Text.from_markup(
                        f"[bold]Parallel Run {action_index}[/bold] ({run_duration})"
                    )
                )
            renderables.append(Text())

            if not step_actions:
                renderables.append(Text("No matching steps"))
                continue

            table = Table(show_header=True, header_style="bold")
            table.add_column("Step")
            table.add_column("Name", overflow="ellipsis", max_width=80)
            table.add_column("Status")
            table.add_column("Duration")

            for step_action in step_actions:
                step_status = _format_step_status(step_action.action.status)
                step_duration = _format_duration(
                    step_action.action.start_time, step_action.action.end_time
                )

                table.add_row(
                    str(step_action.step_index),
                    step_action.step.name,
                    step_status,
                    step_duration,
                )

            renderables.append(table)

        # Combine everything in a panel
        panel = Panel(
            Group(*renderables),
            title=f"[bold]Job {details.number}[/bold]",
            border_style=_get_job_border_style(details.status),
        )
        console.print()
        console.print(panel)
        console.print()


def print_job_output(
    job_output: api_types.JobOutput,
    output_format: flags.OutputFormat,
    try_extract_summary: bool = False,
) -> None:
    if output_format == flags.OutputFormat.json:
        data = [
            {
                "message": Text.from_ansi(msg.message).plain,
                "time": msg.time.isoformat(),
                "truncated": msg.truncated,
                "type": msg.type,
            }
            for msg in job_output
        ]
        console.print(json.dumps(data, indent=2))
    else:
        if not job_output:
            console.print("No output found")
            return

        # Sort by time
        sorted_output = sorted(job_output, key=lambda m: m.time)

        for idx, msg in enumerate(sorted_output):
            # Build heading with type and truncation status
            heading_text = Text()
            heading_text.append(f"# Message: {msg.type}", style="bold")
            if msg.truncated:
                heading_text.append(" (truncated)", style="yellow")
            heading_text.stylize("underline")

            # Normalize line endings (remove extra carriage returns)
            normalized_message = msg.message.replace("\r\r\n", "\n").replace(
                "\r\n", "\n"
            )

            # Print heading
            if idx > 0:
                console.print("\n", end="")
            console.print(heading_text)
            if not normalized_message.startswith("\n"):
                console.print("\n", end="")

            # Try to extract pytest summary if requested
            if try_extract_summary:
                summary = _try_extract_summary(normalized_message)
                if summary:
                    normalized_message = summary

            # Render ANSI content
            content = Text.from_ansi(normalized_message)
            console.print(content)


def _try_extract_summary(message: str) -> str | None:
    """Extract pytest summary from output. Returns None if extraction fails."""
    lines = message.split("\n")

    # Find the "short test summary info" section
    summary_start = None
    for i, line in enumerate(lines):
        plain_line = Text.from_ansi(line).plain
        if plain_line.startswith("===") and "short test summary info" in plain_line.lower():
            summary_start = i
            break

    if summary_start is None:
        return None

    # Find the final summary line (contains "passed", "failed", etc. with timing)
    summary_end = None
    for i in range(summary_start + 1, len(lines)):
        line = lines[i]
        plain_line = Text.from_ansi(line).plain
        # Look for the final summary line with timing info
        if (
            plain_line.startswith("===")
            and ("passed" in plain_line.lower() or "failed" in plain_line.lower())
            and "in " in plain_line.lower()
        ):
            summary_end = i
            break

    if summary_end is None:
        return None

    # Extract the summary section
    summary_lines = lines[summary_start : summary_end + 1]
    return "\n".join(summary_lines)


def _format_duration_ms(duration_ms: int | None) -> str:
    """Format duration from milliseconds."""
    if duration_ms is None:
        return ""
    seconds = duration_ms / 1000
    return humanize.naturaldelta(seconds)


def _format_step_status(status: str) -> str:
    """Format step status with color."""
    if status == "success":
        return f"[green]{status}[/green]"
    elif status == "failed":
        return f"[red]{status}[/red]"
    return str(status)


def _calculate_parallel_run_duration(actions: list[api_types.V1JobAction]) -> str:
    """Calculate duration of a parallel run from its actions."""
    start_times = [a.start_time for a in actions if a.start_time]

    if not start_times:
        return ""

    earliest_start = min(start_times)

    # Check if any actions are still running (no end_time)
    if any(a.end_time is None for a in actions):
        return _format_duration(earliest_start, None)

    # All actions completed - find latest end
    end_times = [a.end_time for a in actions if a.end_time]
    latest_end = max(end_times)
    return _format_duration(earliest_start, latest_end)


def _get_job_border_style(status: api_types.JobStatus) -> str:
    """Get border style for job panel based on status."""
    if status == api_types.JobStatus.success:
        return "green"
    elif status in {
        api_types.JobStatus.failed,
        api_types.JobStatus.infrastructure_fail,
        api_types.JobStatus.timedout,
        api_types.JobStatus.unauthorized,
    }:
        return "red"
    elif status in {
        api_types.JobStatus.running,
        api_types.JobStatus.queued,
    }:
        return "yellow"
    return "white"


def _format_pipeline_state(state: api_types.PipelineState) -> str:
    """Format pipeline state with color."""
    if state == api_types.PipelineState.errored:
        return f"[red]{state}[/red]"
    return str(state)


def _get_pipeline_border_style(
    state: api_types.PipelineState,
    workflows: list[api_types.Workflow],
) -> str:
    """Get border style for pipeline panel based on state and workflow statuses."""
    # Pipeline errors take priority
    if state == api_types.PipelineState.errored:
        return "red"

    if not workflows:
        return "white"

    # Check for failed workflows
    if any(
        w.status
        in {
            api_types.WorkflowStatus.failed,
            api_types.WorkflowStatus.error,
            api_types.WorkflowStatus.failing,
        }
        for w in workflows
    ):
        return "red"

    # Check for running workflows
    if any(w.status == api_types.WorkflowStatus.running for w in workflows):
        return "yellow"

    # Check if all are successful
    if all(w.status == api_types.WorkflowStatus.success for w in workflows):
        return "green"

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
    """Build CircleCI pipeline URL."""
    vcs_provider, org, repo = _parse_project_slug(pipeline.project_slug)
    return f"https://app.circleci.com/pipelines/{vcs_provider}/{org}/{repo}/{pipeline.number}"


def _format_workflow_status(status: api_types.WorkflowStatus) -> str:
    """Format workflow status with color."""
    color = _get_workflow_color(status)
    if color == "white":
        return str(status)
    return f"[{color}]{status}[/{color}]"


def _get_workflow_border_style(status: api_types.WorkflowStatus) -> str:
    """Get border style for workflow panel based on status."""
    return _get_workflow_color(status)


def _format_duration(start: datetime | None, stop: datetime | None) -> str:
    """Format duration between start and stop times."""
    if start is None:
        return ""

    if stop is None:
        # Still running, show elapsed time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - start
        return f"{humanize.naturaldelta(delta)} (running)"

    # Completed, show total duration
    delta = stop - start
    return humanize.naturaldelta(delta)


def _build_workflow_url(workflow: api_types.Workflow) -> str:
    """Build CircleCI workflow URL."""
    vcs_provider, org, repo = _parse_project_slug(workflow.project_slug)
    return f"https://app.circleci.com/pipelines/{vcs_provider}/{org}/{repo}/{workflow.pipeline_number}/workflows/{workflow.id}"


def _format_link(url: str) -> str:
    """Format a clickable link with consistent styling."""
    return f"[link={url}][blue underline]link[/blue underline][/link]"


def _parse_project_slug(project_slug: str) -> tuple[str, str, str]:
    """Parse project_slug into (vcs_provider, org, repo)."""
    parts = project_slug.split("/")
    assert len(parts) == 3, f"Invalid project slug: {project_slug}"
    vcs_provider = "github" if parts[0] == "gh" else "bitbucket"
    org = parts[1]
    repo = parts[2]
    return vcs_provider, org, repo


def _get_workflow_color(status: api_types.WorkflowStatus) -> str:
    """Get color for workflow status."""
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


def _format_job_status(status: api_types.JobStatus) -> str:
    """Format job status with color."""
    if status == api_types.JobStatus.success:
        return f"[green]{status}[/green]"
    elif status in {
        api_types.JobStatus.failed,
        api_types.JobStatus.infrastructure_fail,
        api_types.JobStatus.timedout,
        api_types.JobStatus.unauthorized,
    }:
        return f"[red]{status}[/red]"
    elif status in {
        api_types.JobStatus.running,
        api_types.JobStatus.queued,
    }:
        return f"[yellow]{status}[/yellow]"
    return str(status)


def _get_job_status_priority(status: api_types.JobStatus) -> int:
    """Get priority for job status sorting (lower = higher priority)."""
    # Failed/errored first
    if status in {
        api_types.JobStatus.failed,
        api_types.JobStatus.infrastructure_fail,
        api_types.JobStatus.timedout,
        api_types.JobStatus.unauthorized,
    }:
        return 0
    # Running/queued second
    elif status in {
        api_types.JobStatus.running,
        api_types.JobStatus.queued,
    }:
        return 1
    # Success third
    elif status == api_types.JobStatus.success:
        return 2
    # Everything else last
    else:
        return 3


def _build_job_url(job: api_types.Job) -> str:
    """Build CircleCI job URL."""
    vcs_provider, org, repo = _parse_project_slug(job.project_slug)
    return f"https://app.circleci.com/pipelines/{vcs_provider}/{org}/{repo}/jobs/{job.job_number}"
