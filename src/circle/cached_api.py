import dataclasses
import functools

import diskcache
import platformdirs

from . import api, api_types

_CACHE_SIZE_LIMIT = 1024 * 1024 * 1024  # 1GB


@dataclasses.dataclass(frozen=True)
class CachedAPIClient:
    inner: api.APIClient

    @functools.cached_property
    def _cache(self) -> diskcache.Cache:
        cache_dir = platformdirs.user_cache_dir("circle", "circle-cli")
        return diskcache.Cache(
            cache_dir,
            size_limit=_CACHE_SIZE_LIMIT,
            eviction_policy="least-recently-used",
        )

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
