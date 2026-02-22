"""Markdown output formatting for coding agents."""

from collections import defaultdict
from datetime import datetime, timezone

from rich.text import Text
from tabulate import tabulate

from .. import api_types, service, summary
from ._core import UniqueLevel
from ._common import (
    build_job_url,
    build_pipeline_url,
    build_workflow_url,
    collect_unique_jobs,
    format_failed_test_jobs,
    get_commit_subject,
    get_job_status_priority,
)


class MarkdownOutput:
    def print_pipelines(
        self,
        pipelines: list[service.PipelineWithWorkflows],
    ) -> None:
        if not pipelines:
            print("No pipelines found")
            return

        for p in sorted(pipelines, key=lambda x: x.pipeline.created_at, reverse=True):
            _print_pipeline(p)

    def print_pipeline_detail(
        self,
        pipeline_with_workflows: service.PipelineWithWorkflows,
    ) -> None:
        _print_pipeline(pipeline_with_workflows)

    def print_workflows(
        self,
        workflows_with_jobs: list[service.WorkflowWithJobs],
    ) -> None:
        if not workflows_with_jobs:
            print("No workflows found")
            return

        # Group by pipeline_id
        by_pipeline: dict[str, list[service.WorkflowWithJobs]] = defaultdict(list)
        for wj in workflows_with_jobs:
            by_pipeline[wj.workflow.pipeline_id].append(wj)

        for pipeline_id, pipeline_wjs in by_pipeline.items():
            print(f"\n## Pipeline: {pipeline_id}\n")

            for wj in sorted(pipeline_wjs, key=lambda x: x.workflow.created_at):
                workflow = wj.workflow
                duration = _duration(workflow.created_at, workflow.stopped_at)
                url = build_workflow_url(workflow)
                job_summary = _job_summary(wj.job_counts_by_status)

                print(f"### {workflow.name} ({workflow.id})")
                print(f"- **Status:** {workflow.status}")
                print(f"- **Created:** {_timestamp(workflow.created_at)}")
                print(f"- **Duration:** {duration}")
                print(f"- **Jobs:** {job_summary}")
                print(f"- **Link:** {url}")
                print()

    def print_jobs(
        self,
        jobs: list[service.WorkflowWithJobs],
    ) -> None:
        if not jobs:
            print("No jobs found")
            return

        for wj in sorted(jobs, key=lambda x: x.workflow.created_at):
            workflow, job_list = wj.workflow, wj.jobs
            job_summary = _job_summary(wj.job_counts_by_status)

            print(f"\n## Workflow: {workflow.name} ({workflow.id})")
            print(f"Jobs: {job_summary}\n")

            if not job_list:
                print("No jobs matching filter")
            else:
                sorted_jobs = sorted(
                    job_list, key=lambda j: get_job_status_priority(j.status)
                )

                rows = []
                for job in sorted_jobs:
                    started = _timestamp(job.started_at) if job.started_at else ""
                    duration = _duration(job.started_at, job.stopped_at)
                    link = build_job_url(job) if job.job_number is not None else ""

                    rows.append(
                        [
                            str(job.job_number or ""),
                            job.name,
                            str(job.status),
                            started,
                            duration,
                            link,
                        ]
                    )

                print(
                    tabulate(
                        rows,
                        headers=[
                            "Number",
                            "Name",
                            "Status",
                            "Started",
                            "Duration",
                            "Link",
                        ],
                        tablefmt="github",
                    )
                )
            print()

    def print_job_details(
        self,
        job_details: service.JobDetailsWithSteps,
    ) -> None:
        details = job_details.details
        duration = _duration_ms(details.duration)

        print(f"\n## Job {details.number}")
        print(f"- **Name:** {details.name}")
        print(f"- **Status:** {details.status}")
        print(f"- **Started:** {_timestamp(details.started_at)}")
        print(f"- **Duration:** {duration}")
        print(f"- **Parallelism:** {details.parallelism}")
        print(f"- **Link:** {details.web_url}")

        for action_index in sorted(job_details.steps_by_action_index.keys()):
            step_actions = job_details.steps_by_action_index[action_index]

            if details.parallelism > 1:
                actions = [sa.action for sa in step_actions]
                run_duration = _parallel_run_duration(actions)
                print(f"\n### Parallel Run {action_index} ({run_duration})\n")
            else:
                print("\n### Steps\n")

            if not step_actions:
                print("No steps matching filter")
                continue

            rows = []
            for step_action in step_actions:
                step_duration = _duration(
                    step_action.action.start_time, step_action.action.end_time
                )
                rows.append(
                    [
                        str(step_action.step_index),
                        step_action.step.name,
                        step_action.action.status,
                        step_duration,
                    ]
                )

            print(
                tabulate(
                    rows,
                    headers=["Step", "Name", "Status", "Duration"],
                    tablefmt="github",
                )
            )
        print()

    def print_job_tests(
        self,
        tests: list[api_types.JobTestMetadata],
        include_messages: bool,
    ) -> None:
        if not tests:
            print("No tests found")
            return

        # Group by file, then by classname
        by_file: dict[str, dict[str, list[api_types.JobTestMetadata]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for test in tests:
            by_file[test.file or ""][test.classname].append(test)

        for file in sorted(by_file.keys()):
            classnames = by_file[file]
            failed_tests: list[api_types.JobTestMetadata] = []

            print(f"\n## File: {file}\n")

            for classname in sorted(classnames.keys()):
                class_tests = sorted(classnames[classname], key=lambda t: t.name)

                failed_tests.extend(
                    t
                    for t in class_tests
                    if t.result == api_types.JobTestResult.failure
                )

                print(f"### {classname}\n")

                rows = []
                for test in class_tests:
                    rows.append(
                        [
                            str(test.result),
                            test.name,
                            f"{test.run_time:.2f}s",
                        ]
                    )

                print(
                    tabulate(
                        rows,
                        headers=["Result", "Name", "Duration"],
                        tablefmt="github",
                    )
                )
                print()

            if include_messages and failed_tests:
                print("### Failure Messages\n")
                for test in failed_tests:
                    print(f"**{test.name}**")
                    if test.message:
                        print(test.message)
                    else:
                        print("(no message)")
                    print()

    def print_workflow_failed_tests(
        self,
        workflow_failed_tests: service.WorkflowFailedTests,
        unique: UniqueLevel | None,
        include_jobs: bool,
    ) -> None:
        workflow = workflow_failed_tests.workflow
        failed_tests = workflow_failed_tests.failed_tests

        if not failed_tests:
            print("No failed tests found")
            return

        url = build_workflow_url(workflow)

        print(f"\n## Workflow: {workflow.name} ({workflow.id})")
        print(f"- **Status:** {workflow.status}")
        total = sum(
            1
            for by_cls in failed_tests.values()
            for by_name in by_cls.values()
            for _name in by_name
        )
        print(f"- **Failed tests:** {total}")
        print(f"- **Link:** {url}")
        print()

        for file, by_classname in failed_tests.items():
            if unique == UniqueLevel.file:
                file_count = sum(len(names) for names in by_classname.values())
                print(f"- {file or '(no file)'} [{file_count} fails]")
                if include_jobs:
                    all_jobs = collect_unique_jobs(
                        ji
                        for by_name in by_classname.values()
                        for infos in by_name.values()
                        for ji in infos
                    )
                    print(f"  - Jobs: {format_failed_test_jobs(all_jobs)}")
                continue

            file_count = sum(len(names) for names in by_classname.values())
            print(f"- {file or '(no file)'} [{file_count} fails]")
            for classname, by_name in by_classname.items():
                if unique == UniqueLevel.classname:
                    print(f"  - {classname} [{len(by_name)} fails]")
                    if include_jobs:
                        all_jobs = collect_unique_jobs(
                            ji for infos in by_name.values() for ji in infos
                        )
                        print(f"    - Jobs: {format_failed_test_jobs(all_jobs)}")
                    continue

                print(f"  - {classname} [{len(by_name)} fails]")
                for name, job_infos in by_name.items():
                    print(f"    - {name}")
                    if include_jobs:
                        print(f"      - Jobs: {format_failed_test_jobs(job_infos)}")

    def print_job_output(
        self,
        job_output: api_types.JobOutput,
        try_extract_summary: bool,
    ) -> None:
        if not job_output:
            print("No output found")
            return

        sorted_output = sorted(job_output, key=lambda m: m.time)

        for msg in sorted_output:
            # Normalize line endings
            normalized_message = msg.message.replace("\r\r\n", "\n").replace(
                "\r\n", "\n"
            )

            # Try to extract summary if requested
            is_summary = False
            if try_extract_summary:
                summary_ = summary.try_extract_summary(normalized_message)
                if summary_ is not None:
                    normalized_message = summary_
                    is_summary = True

            # Build header
            title = f"## {msg.type}"
            if msg.truncated:
                title += " (truncated)"
            if is_summary:
                title += " (summary)"

            print(f"\n{title}\n")

            # Strip ANSI codes and print plain text
            plain_text = Text.from_ansi(normalized_message.strip()).plain
            print(plain_text)
            print()


def _print_pipeline(p: service.PipelineWithWorkflows) -> None:
    pipeline, workflows = p.pipeline, p.workflows
    commit = get_commit_subject(pipeline)
    url = build_pipeline_url(pipeline)
    commit_hash = (
        pipeline.vcs.revision[:7]
        if pipeline.vcs and pipeline.vcs.revision
        else "unknown"
    )

    sorted_workflows = sorted(workflows, key=lambda w: w.created_at)
    workflow_status = ", ".join(f"{w.name}: {w.status}" for w in sorted_workflows)

    branch = pipeline.vcs.branch if pipeline.vcs and pipeline.vcs.branch else "unknown"

    print(f"\n## Pipeline {pipeline.number} ({pipeline.state})")
    print(f"- **ID:** {pipeline.id}")
    print(f"- **Created:** {_timestamp(pipeline.created_at)}")
    print(f"- **Branch:** {branch}")
    print(f"- **Commit:** {commit_hash} {commit}")
    print(f"- **Triggered by:** {pipeline.trigger.actor.login}")
    print(f"- **Workflows:** {workflow_status}")
    print(f"- **Link:** {url}")

    if pipeline.errors:
        print("- **Errors:**")
        for e in pipeline.errors:
            print(f"  - {e.type}: {e.message}")

    print()


def _timestamp(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _duration(start: datetime | None, stop: datetime | None) -> str:
    if start is None:
        return ""
    if stop is None:
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - start
        return f"{int(delta.total_seconds())}s (running)"
    return f"{int((stop - start).total_seconds())}s"


def _duration_ms(duration_ms: int | None) -> str:
    if duration_ms is None:
        return ""
    return f"{duration_ms // 1000}s"


def _job_summary(counts: dict[api_types.JobStatus, int]) -> str:
    if not counts:
        return "no jobs"

    running = counts.get(api_types.JobStatus.running, 0)
    success = counts.get(api_types.JobStatus.success, 0)
    failed = counts.get(api_types.JobStatus.failed, 0)
    other = sum(counts.values()) - running - success - failed

    parts: list[str] = []
    if running:
        parts.append(f"{running} running")
    if success:
        parts.append(f"{success} success")
    if failed:
        parts.append(f"{failed} failed")
    if other:
        parts.append(f"{other} other")

    return ", ".join(parts)


def _parallel_run_duration(actions: list[api_types.V1JobAction]) -> str:
    start_times = [a.start_time for a in actions if a.start_time]
    if not start_times:
        return ""

    earliest_start = min(start_times)

    if any(a.end_time is None for a in actions):
        return _duration(earliest_start, None)

    end_times = [a.end_time for a in actions if a.end_time]
    latest_end = max(end_times)
    return _duration(earliest_start, latest_end)
