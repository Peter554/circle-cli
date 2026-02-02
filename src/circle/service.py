import asyncio
import dataclasses
from collections.abc import Set

from . import api, api_types, cache_manager, config, git


class AppError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class AppService:
    app_config: config.AppConfig
    api_client: api.APIClient
    cache_manager: cache_manager.CacheManager

    async def get_latest_pipeline(
        self,
        branch: str | None,
    ) -> api_types.Pipeline | None:
        branch = self._get_branch(branch)

        pipeline = self.cache_manager.get_latest_pipeline(branch)
        if pipeline is None:
            pipelines = await self.api_client.get_latest_pipelines(
                self.app_config.project_slug, branch, 1
            )
            pipeline = pipelines[0] if pipelines else None
            self.cache_manager.set_latest_pipeline(branch, pipeline)

        return pipeline

    async def get_latest_pipelines(
        self,
        branch: str | None,
        n: int,
    ) -> list[tuple[api_types.Pipeline, list[api_types.Workflow]]]:
        branch = self._get_branch(branch)

        pipelines = self.cache_manager.get_latest_pipelines(branch, n)
        if pipelines is None:
            pipelines = await self.api_client.get_latest_pipelines(
                self.app_config.project_slug, branch, n
            )
            self.cache_manager.set_latest_pipelines(branch, pipelines, n)

        # Fetch workflows for all pipelines concurrently
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self.get_pipeline_workflows(pipeline.id))
                for pipeline in pipelines
            ]
        workflows_lists = [task.result() for task in tasks]

        # Pair pipelines with their workflows
        return list(zip(pipelines, workflows_lists))

    async def get_pipeline_workflows(
        self,
        pipeline_id: str | None,
    ) -> list[api_types.Workflow]:
        # If no pipeline ID provided, get the latest pipeline for current branch
        if pipeline_id is None:
            pipeline_id = (await self._get_latest_pipeline_for_current_branch()).id

        workflows = self.cache_manager.get_pipeline_workflows(pipeline_id)
        if workflows is None:
            workflows = await self.api_client.get_workflows(pipeline_id)
            self.cache_manager.set_pipeline_workflows(pipeline_id, workflows)

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
            workflows = await self.get_pipeline_workflows(pipeline_id)

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

    async def get_job_output(self, job_number: int) -> api_types.V1JobDetail:
        """Get job output."""
        # TODO Fetch output from output_url
        # TODO Caching
        return await self.api_client.get_v1_job_detail(
            self.app_config.project_slug, job_number
        )

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
        workflow = self.cache_manager.get_workflow(workflow_id)
        if workflow is None:
            workflow = await self.api_client.get_workflow(workflow_id)
            self.cache_manager.set_workflow(workflow)
        return workflow

    async def _get_workflow_jobs(
        self, workflow: api_types.Workflow
    ) -> list[api_types.Job]:
        jobs = self.cache_manager.get_workflow_jobs(workflow.id)
        if jobs is None:
            jobs = await self.api_client.get_jobs(workflow.id)
            self.cache_manager.set_workflow_jobs(workflow.id, workflow.status, jobs)
        return jobs
