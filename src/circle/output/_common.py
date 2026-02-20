"""Shared helpers used across output implementations."""

from .. import api_types


def build_pipeline_url(pipeline: api_types.Pipeline) -> str:
    """Build CircleCI pipeline URL."""
    vcs_provider, org, repo = parse_project_slug(pipeline.project_slug)
    return f"https://app.circleci.com/pipelines/{vcs_provider}/{org}/{repo}/{pipeline.number}"


def build_workflow_url(workflow: api_types.Workflow) -> str:
    """Build CircleCI workflow URL."""
    vcs_provider, org, repo = parse_project_slug(workflow.project_slug)
    return f"https://app.circleci.com/pipelines/{vcs_provider}/{org}/{repo}/{workflow.pipeline_number}/workflows/{workflow.id}"


def build_job_url(job: api_types.Job) -> str:
    """Build CircleCI job URL."""
    vcs_provider, org, repo = parse_project_slug(job.project_slug)
    return f"https://app.circleci.com/pipelines/{vcs_provider}/{org}/{repo}/jobs/{job.job_number}"


def parse_project_slug(project_slug: str) -> tuple[str, str, str]:
    """Parse project_slug into (vcs_provider, org, repo)."""
    parts = project_slug.split("/")
    assert len(parts) == 3, f"Invalid project slug: {project_slug}"
    vcs_provider = "github" if parts[0] == "gh" else "bitbucket"
    org = parts[1]
    repo = parts[2]
    return vcs_provider, org, repo


def get_commit_subject(pipeline: api_types.Pipeline) -> str:
    """Get commit subject."""
    if pipeline.vcs and pipeline.vcs.commit and pipeline.vcs.commit.subject:
        return pipeline.vcs.commit.subject
    return ""


def get_job_status_priority(status: api_types.JobStatus) -> int:
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
