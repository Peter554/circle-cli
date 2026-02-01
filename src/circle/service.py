import asyncio
import dataclasses
from collections.abc import Set
from datetime import datetime, timedelta, timezone

from . import api, api_types, cache, config, git


class AppError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class AppService:
    app_config: config.AppConfig
    api_client: api.APIClient
    api_cache: cache.Cache
    in_progress_ttl_seconds: int = 5

    async def get_latest_pipeline(
        self,
        branch: str | None,
    ) -> api_types.Pipeline | None:
        branch = self._get_branch(branch)
        cache_key = f"latest_pipeline:{self.app_config.project_slug}:{branch}"
        pipeline = self.api_cache.get(cache_key)
        if pipeline is None:
            pipelines = await self.api_client.get_pipelines(
                self.app_config.project_slug, branch, 1
            )
            pipeline = pipelines[0] if pipelines else None
            self.api_cache.set(cache_key, pipeline, ttl=self.in_progress_ttl_seconds)
        return pipeline

    async def get_pipelines(
        self,
        branch: str | None,
        n: int,
    ) -> list[tuple[api_types.Pipeline, list[api_types.Workflow]]]:
        branch = self._get_branch(branch)
        cache_key = f"pipelines:{self.app_config.project_slug}:{branch}:{n}"
        pipelines = self.api_cache.get(cache_key)
        if pipelines is None:
            pipelines = await self.api_client.get_pipelines(
                self.app_config.project_slug, branch, n
            )
            # No concept of pipeline completion.
            self.api_cache.set(cache_key, pipelines, ttl=self.in_progress_ttl_seconds)

        # Fetch workflows for all pipelines concurrently
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self.get_workflows(pipeline.id))
                for pipeline in pipelines
            ]
        workflows_lists = [task.result() for task in tasks]

        # Pair pipelines with their workflows
        return list(zip(pipelines, workflows_lists))

    async def get_workflows(
        self,
        pipeline_id: str | None,
    ) -> list[api_types.Workflow]:
        # If no pipeline ID provided, get the latest pipeline for current branch
        if pipeline_id is None:
            pipeline_id = (await self._get_latest_pipeline_for_current_branch()).id

        cache_key = f"pipeline:{pipeline_id}:workflows"
        workflows = self.api_cache.get(cache_key)
        if workflows is None:
            workflows = await self.api_client.get_workflows(pipeline_id)
            # No concept of pipeline completion.
            # Infer completion based on workflows.
            # Cache indefinitely only if all workflows stopped more than one minutes ago
            cache_indefinitely = len(workflows) > 0 and all(
                w.is_completed
                and w.stopped_at is not None
                and w.stopped_at < datetime.now(timezone.utc) - timedelta(minutes=1)
                for w in workflows
            )

            ttl = None if cache_indefinitely else self.in_progress_ttl_seconds
            self.api_cache.set(cache_key, workflows, ttl=ttl)
        return workflows

    async def get_jobs(
        self,
        pipeline_id: str | None,
        workflow_ids: list[str] | None,
        statuses: Set[api_types.JobStatus] | None = None,
    ) -> list[tuple[api_types.Workflow, list[api_types.Job]]]:
        # If workflow IDs are provided use those. If pipeline ID was provided validate it against the workflows.
        # If no workflow IDs are, use workflows for the pipeline ID or latest pipeline for the current branch.

        if workflow_ids:
            # Fetch all workflows concurrently
            async with asyncio.TaskGroup() as tg:
                tasks = [
                    tg.create_task(self._get_workflow(wid)) for wid in workflow_ids
                ]
            workflows = [task.result() for task in tasks]
        else:
            if pipeline_id is None:
                pipeline_id = (await self._get_latest_pipeline_for_current_branch()).id
            workflows = await self.get_workflows(pipeline_id)

        # Validate pipeline_id if provided
        if pipeline_id is not None:
            for workflow in workflows:
                if workflow.pipeline_id != pipeline_id:
                    raise AppError(
                        f"Workflow {workflow.id} does not belong to pipeline {pipeline_id}"
                    )

        # Fetch jobs for all workflows concurrently
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self._get_workflow_jobs(workflow))
                for workflow in workflows
            ]
        jobs_lists = [task.result() for task in tasks]

        # Filter jobs by status if specified
        if statuses is not None:
            jobs_lists = [
                [job for job in jobs if job.status in statuses] for jobs in jobs_lists
            ]

        # Pair workflows with their jobs
        return list(zip(workflows, jobs_lists))

    @staticmethod
    def _get_branch(branch: str | None) -> str:
        branch = branch or git.get_current_branch()
        if branch is None:
            raise AppError("Branch could not be determined")
        return branch

    async def _get_latest_pipeline_for_current_branch(self) -> api_types.Pipeline:
        branch = self._get_branch(None)
        pipeline = await self.get_latest_pipeline(branch)
        if not pipeline:
            raise AppError(f"No pipelines found (branch '{branch}')")
        return pipeline

    async def _get_workflow(self, workflow_id: str) -> api_types.Workflow:
        cache_key = f"workflow:{workflow_id}"
        workflow = self.api_cache.get(cache_key)
        if workflow is None:
            workflow = await self.api_client.get_workflow(workflow_id)
            ttl = None if workflow.is_completed else self.in_progress_ttl_seconds
            self.api_cache.set(cache_key, workflow, ttl=ttl)
        return workflow

    async def _get_workflow_jobs(
        self, workflow: api_types.Workflow
    ) -> list[api_types.Job]:
        cache_key = f"workflow:{workflow.id}:jobs"
        jobs = self.api_cache.get(cache_key)
        if jobs is None:
            jobs = await self.api_client.get_jobs(workflow.id)
            ttl = None if workflow.is_completed else self.in_progress_ttl_seconds
            self.api_cache.set(cache_key, jobs, ttl=ttl)
        return jobs


def _dt_less_than(dt: datetime | None, dt2: datetime) -> bool:
    return dt is not None and dt < dt2
