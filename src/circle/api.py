from __future__ import annotations

import dataclasses

import httpx

from . import api_types


class APIError(Exception): ...


@dataclasses.dataclass(frozen=True)
class APIClient:
    token: str
    base_url_v2: str = dataclasses.field(
        default="https://circleci.com/api/v2", init=False
    )

    async def get_pipelines(
        self, project_slug: str, branch: str, limit: int
    ) -> list[api_types.Pipeline]:
        """
        GET /project/{project_slug}/pipeline?branch={branch}
        """
        url = f"{self.base_url_v2}/project/{project_slug}/pipeline"
        params = {"branch": branch}
        items = await self._fetch_paginated(url, params, max_items=limit)
        return [api_types.Pipeline.model_validate(item) for item in items]

    async def get_workflows(self, pipeline_id: str) -> list[api_types.Workflow]:
        """
        GET /pipeline/{pipeline-id}/workflow
        """
        url = f"{self.base_url_v2}/pipeline/{pipeline_id}/workflow"
        items = await self._fetch_paginated(url, max_items=None)
        return [api_types.Workflow.model_validate(item) for item in items]

    async def get_workflow(self, workflow_id: str) -> api_types.Workflow:
        """
        GET /workflow/{id}
        """
        url = f"{self.base_url_v2}/workflow/{workflow_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers(), timeout=30)
            if response.status_code != 200:
                raise APIError(
                    f"Failed to fetch from {url}: {response.status_code} {response.text}"
                )
            return api_types.Workflow.model_validate(response.json())

    async def get_jobs(self, workflow_id: str) -> list[api_types.Job]:
        """
        GET /workflow/{id}/job
        """
        url = f"{self.base_url_v2}/workflow/{workflow_id}/job"
        items = await self._fetch_paginated(url, max_items=None)
        return [api_types.Job.model_validate(item) for item in items]

    def _headers(self) -> dict[str, str]:
        return {"Circle-Token": self.token}

    async def _fetch_paginated(
        self,
        url: str,
        params: dict[str, str] | None = None,
        max_items: int | None = None,
    ) -> list[dict]:
        params = params or {}
        all_items = []
        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    url, headers=self._headers(), params=params, timeout=30
                )
                if response.status_code != 200:
                    raise APIError(
                        f"Failed to fetch from {url}: {response.status_code} {response.text}"
                    )

                data = response.json()
                items = data.get("items", [])
                all_items.extend(items)

                # Check if we've reached the limit
                if max_items is not None and len(all_items) >= max_items:
                    return all_items[:max_items]

                # Check for next page
                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break

                # Add page token for next request
                params["page-token"] = next_page_token

        return all_items
