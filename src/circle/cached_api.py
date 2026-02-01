import dataclasses

from . import api, api_types


@dataclasses.dataclass(frozen=True)
class CachedAPIClient:
    inner: api.APIClient

    async def get_pipelines(
        self, project_slug: str, branch: str, limit: int
    ) -> list[api_types.Pipeline]:
        return await self.inner.get_pipelines(project_slug, branch, limit)

    async def get_workflows(self, pipeline_id: str) -> list[api_types.Workflow]:
        return await self.inner.get_workflows(pipeline_id)

    async def get_workflow(self, workflow_id: str) -> api_types.Workflow:
        return await self.inner.get_workflow(workflow_id)

    async def get_jobs(self, workflow_id: str) -> list[api_types.Job]:
        return await self.inner.get_jobs(workflow_id)
