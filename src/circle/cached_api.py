import dataclasses
import functools
import logging

import diskcache
import platformdirs

from . import api, api_types

_CACHE_SIZE_LIMIT = 1024 * 1024 * 1024  # 1GB
_IN_PROGRESS_TTL = 15  # Seconds

logger = logging.getLogger(__name__)


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
        cache_key = f"workflows:{pipeline_id}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit: %s", cache_key)
            return cached

        logger.info("Cache miss: %s", cache_key)
        workflows = await self.inner.get_workflows(pipeline_id)

        if workflows and all(workflow.is_completed for workflow in workflows):
            ttl = None
        else:
            ttl = _IN_PROGRESS_TTL

        self._cache.set(cache_key, workflows, expire=ttl)
        return workflows

    async def get_workflow(self, workflow_id: str) -> api_types.Workflow:
        cache_key = f"workflow:{workflow_id}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit: %s", cache_key)
            return cached

        logger.info("Cache miss: %s", cache_key)
        workflow = await self.inner.get_workflow(workflow_id)

        if workflow.is_completed:
            ttl = None
        else:
            ttl = _IN_PROGRESS_TTL

        self._cache.set(cache_key, workflow, expire=ttl)
        return workflow

    async def get_jobs(self, workflow_id: str) -> list[api_types.Job]:
        cache_key = f"jobs:{workflow_id}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit: %s", cache_key)
            return cached

        logger.info("Cache miss: %s", cache_key)
        jobs = await self.inner.get_jobs(workflow_id)

        if jobs and all(job.is_completed for job in jobs):
            ttl = None
        else:
            ttl = _IN_PROGRESS_TTL

        self._cache.set(cache_key, jobs, expire=ttl)
        return jobs
