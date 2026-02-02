import dataclasses
from datetime import datetime, timedelta, timezone

from . import api_types, cache


@dataclasses.dataclass(frozen=True)
class CacheManager:
    cache: cache.Cache
    in_progress_ttl_seconds: int = 5

    def get_latest_pipeline(self, branch: str) -> api_types.Pipeline | None:
        cache_key = f"branch:{branch}:latest_pipeline"
        return self.cache.get(cache_key)

    def set_latest_pipeline(
        self, branch: str, pipeline: api_types.Pipeline | None
    ) -> None:
        cache_key = f"branch:{branch}:latest_pipeline"
        self.cache.set(cache_key, pipeline, ttl=self.in_progress_ttl_seconds)

    def get_latest_pipelines(
        self, branch: str, n: int
    ) -> list[api_types.Pipeline] | None:
        cache_key = f"branch:{branch}:latest_pipelines:{n}"
        return self.cache.get(cache_key)

    def set_latest_pipelines(
        self, branch: str, pipelines: list[api_types.Pipeline], n: int
    ) -> None:
        cache_key = f"branch:{branch}:latest_pipelines:{n}"
        self.cache.set(cache_key, pipelines, ttl=self.in_progress_ttl_seconds)

        self.set_latest_pipeline(branch, pipelines[0])

    def get_workflow(self, workflow_id: str) -> api_types.Workflow | None:
        cache_key = f"workflow:{workflow_id}"
        return self.cache.get(cache_key)

    def set_workflow(self, workflow: api_types.Workflow) -> None:
        cache_key = f"workflow:{workflow.id}"
        ttl = (
            None
            if _workflow_is_finished(workflow.status)
            else self.in_progress_ttl_seconds
        )
        self.cache.set(cache_key, workflow, ttl=ttl)

    def get_pipeline_workflows(
        self, pipeline_id: str
    ) -> list[api_types.Workflow] | None:
        cache_key = f"pipeline:{pipeline_id}:workflows"
        return self.cache.get(cache_key)

    def set_pipeline_workflows(
        self, pipeline_id: str, workflows: list[api_types.Workflow]
    ) -> None:
        cache_key = f"pipeline:{pipeline_id}:workflows"

        # No concept of pipeline completion.
        # Infer completion based on workflows.
        # Cache indefinitely only if all workflows stopped more than one minute ago.
        cache_indefinitely = workflows and all(
            _workflow_is_finished(w.status)
            and w.stopped_at is not None
            and w.stopped_at < datetime.now(timezone.utc) - timedelta(minutes=1)
            for w in workflows
        )
        ttl = None if cache_indefinitely else self.in_progress_ttl_seconds

        self.cache.set(cache_key, workflows, ttl=ttl)

        for workflow in workflows:
            self.set_workflow(workflow)

    def get_workflow_jobs(self, workflow_id: str) -> list[api_types.Job] | None:
        cache_key = f"workflow:{workflow_id}:jobs"
        return self.cache.get(cache_key)

    def set_workflow_jobs(
        self,
        workflow_id: str,
        workflow_status: api_types.WorkflowStatus,
        jobs: list[api_types.Job],
    ) -> None:
        cache_key = f"workflow:{workflow_id}:jobs"
        ttl = (
            None
            if _workflow_is_finished(workflow_status)
            else self.in_progress_ttl_seconds
        )
        self.cache.set(cache_key, jobs, ttl=ttl)

    def get_v1_job_details(self, job_number: int) -> api_types.V1JobDetails | None:
        cache_key = f"v1_job_details:{job_number}:details"
        return self.cache.get(cache_key)

    def set_v1_job_details(
        self,
        job_number: int,
        job_details: api_types.V1JobDetails,
    ) -> None:
        cache_key = f"v1_job_details:{job_number}:details"
        ttl = (
            None
            if _v1_job_is_finished(job_details.lifecycle)
            else self.in_progress_ttl_seconds
        )
        self.cache.set(cache_key, job_details, ttl=ttl)


def _workflow_is_finished(workflow_status: api_types.WorkflowStatus) -> bool:
    return workflow_status in {
        api_types.WorkflowStatus.success,
        api_types.WorkflowStatus.failed,
        api_types.WorkflowStatus.error,
        api_types.WorkflowStatus.canceled,
        api_types.WorkflowStatus.unauthorized,
    }


def _job_is_finished(job_status: api_types.JobStatus) -> bool:
    return job_status in {
        api_types.JobStatus.success,
        api_types.JobStatus.failed,
        api_types.JobStatus.canceled,
        api_types.JobStatus.unauthorized,
        api_types.JobStatus.not_run,  # Is this the same as "skipped"?
    }


def _v1_job_is_finished(job_lifecycle: api_types.V1JobLifecycle) -> bool:
    return job_lifecycle == api_types.V1JobLifecycle.finished
