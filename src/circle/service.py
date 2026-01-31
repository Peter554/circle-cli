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
        branch: str,
    ) -> api_types.Pipeline | None:
        pipelines = await self.api_client.get_pipelines(
            self.app_config.project_slug, branch, 1
        )
        return pipelines[0] if pipelines else None

    async def get_pipelines(
        self,
        branch: str | None,
        n: int,
    ) -> list[api_types.Pipeline]:
        branch = _get_branch(branch)
        return await self.api_client.get_pipelines(
            self.app_config.project_slug, branch, n
        )

    async def get_workflows(
        self,
        pipeline_id: str | None,
    ) -> list[api_types.Workflow]:
        # If no pipeline ID provided, get the latest pipeline for current branch
        if pipeline_id is None:
            branch = _get_branch(None)
            pipeline = await self.get_latest_pipeline(branch)
            if not pipeline:
                raise AppError(f"No pipelines found (branch '{branch}')")
            pipeline_id = pipeline.id

        return await self.api_client.get_workflows(pipeline_id)


def _get_branch(branch: str | None) -> str:
    branch = branch or git.get_current_branch()
    if branch is None:
        raise AppError("Branch could not be determined")
    return branch
