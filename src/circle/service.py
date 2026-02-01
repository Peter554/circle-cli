import asyncio
import dataclasses

from . import api, api_types, config, git


class AppError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class AppService:
    app_config: config.AppConfig
    api_client: api.APIClient

    async def get_latest_pipeline(
        self,
        branch: str | None,
    ) -> api_types.Pipeline | None:
        branch = self._get_branch(branch)
        pipelines = await self.api_client.get_pipelines(
            self.app_config.project_slug, branch, 1
        )
        return pipelines[0] if pipelines else None

    async def get_pipelines(
        self,
        branch: str | None,
        n: int,
    ) -> list[api_types.Pipeline]:
        branch = self._get_branch(branch)
        return await self.api_client.get_pipelines(
            self.app_config.project_slug, branch, n
        )

    async def get_workflows(
        self,
        pipeline_id: str | None,
    ) -> list[api_types.Workflow]:
        # If no pipeline ID provided, get the latest pipeline for current branch
        if pipeline_id is None:
            pipeline_id = (await self._get_latest_pipeline_for_current_branch()).id

        return await self.api_client.get_workflows(pipeline_id)

    async def get_jobs(
        self,
        pipeline_id: str | None,
        workflow_ids: list[str] | None,
    ) -> list[tuple[api_types.Workflow, list[api_types.Job]]]:
        # If workflow IDs are provided use those. If pipeline ID was provided validate it against the workflows.
        # If no workflow IDs are, use workflows for the pipeline ID or latest pipeline for the current branch.

        if workflow_ids:
            # Fetch all workflows concurrently
            async with asyncio.TaskGroup() as tg:
                tasks = [
                    tg.create_task(self.api_client.get_workflow(wid))
                    for wid in workflow_ids
                ]
            workflows = [task.result() for task in tasks]
        else:
            if pipeline_id is None:
                pipeline_id = (await self._get_latest_pipeline_for_current_branch()).id
            workflows = await self.api_client.get_workflows(pipeline_id)

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
                tg.create_task(self.api_client.get_jobs(workflow.id))
                for workflow in workflows
            ]
        jobs_lists = [task.result() for task in tasks]

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
