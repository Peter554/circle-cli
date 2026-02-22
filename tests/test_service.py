from unittest.mock import create_autospec

import pytest

from circle import api, api_types
from circle.cache_manager import CacheManager
from circle.service import (
    ANY_BRANCH,
    CURRENT_BRANCH,
    AppError,
    AppService,
    FailedTestJobInfo,
    PipelineWithWorkflows,
    StepAction,
    WorkflowWithJobs,
)
from tests.conftest import (
    FakeCache,
    make_job,
    make_job_details,
    make_job_output_message,
    make_job_test,
    make_pipeline,
    make_v1_job_details,
    make_workflow,
)


def assert_awaited_with_args(mock, *expected_args):
    """Assert mock was awaited exactly once for each expected arg set, in any order."""
    assert mock.await_count == len(expected_args)
    for args in expected_args:
        mock.assert_any_await(*args)


def make_service(mock_api=None) -> AppService:
    if mock_api is None:
        mock_api = create_autospec(api.APIClient, instance=True)
    return AppService(
        project_slug="gh/org/repo",
        api_client=mock_api,
        cache_manager=CacheManager(cache=FakeCache()),
    )


class TestGetPipeline:
    @pytest.mark.asyncio
    async def test_not_cached(self):
        pipeline = make_pipeline(id="pipe-1")
        workflows = [make_workflow(pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_pipeline_by_id.return_value = pipeline
        mock_api.get_pipeline_workflows.return_value = workflows

        service = make_service(mock_api)

        result = await service.get_pipeline("pipe-1")

        assert result == PipelineWithWorkflows(pipeline=pipeline, workflows=workflows)
        mock_api.get_pipeline_by_id.assert_awaited_once_with("pipe-1")
        mock_api.get_pipeline_workflows.assert_awaited_once_with("pipe-1")
        assert service.cache_manager.get_pipeline("pipe-1") == pipeline
        assert service.cache_manager.get_pipeline_workflows("pipe-1") == workflows

    @pytest.mark.asyncio
    async def test_cached(self):
        pipeline = make_pipeline(id="pipe-1")
        workflows = [make_workflow(pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_pipeline(pipeline)
        service.cache_manager.set_pipeline_workflows("pipe-1", workflows)

        result = await service.get_pipeline("pipe-1")

        assert result == PipelineWithWorkflows(pipeline=pipeline, workflows=workflows)
        mock_api.get_pipeline_by_id.assert_not_awaited()
        mock_api.get_pipeline_workflows.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_by_number(self):
        pipeline = make_pipeline(id="pipe-1", number=42)
        workflows = [make_workflow(pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_pipeline_by_number.return_value = pipeline
        mock_api.get_pipeline_workflows.return_value = workflows

        service = make_service(mock_api)
        result = await service.get_pipeline("42")

        assert result == PipelineWithWorkflows(pipeline=pipeline, workflows=workflows)
        mock_api.get_pipeline_by_number.assert_awaited_once_with("gh/org/repo", 42)
        # _resolve_pipeline_id already cached the pipeline
        mock_api.get_pipeline_by_id.assert_not_awaited()
        assert service.cache_manager.get_pipeline_id_by_number(42) == "pipe-1"
        assert service.cache_manager.get_pipeline("pipe-1") == pipeline

    @pytest.mark.asyncio
    async def test_by_number_cached(self):
        pipeline = make_pipeline(id="pipe-1")
        workflows = [make_workflow(pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_pipeline_by_id.return_value = pipeline
        mock_api.get_pipeline_workflows.return_value = workflows

        service = make_service(mock_api)
        service.cache_manager.set_pipeline_id_by_number(42, "pipe-1")

        result = await service.get_pipeline("42")

        assert result == PipelineWithWorkflows(pipeline=pipeline, workflows=workflows)
        mock_api.get_pipeline_by_number.assert_not_awaited()
        mock_api.get_pipeline_by_id.assert_awaited_once_with("pipe-1")


class TestGetLatestPipeline:
    @pytest.mark.asyncio
    async def test_not_cached(self):
        pipeline = make_pipeline()

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_latest_pipelines_for_branch.return_value = [pipeline]

        service = make_service(mock_api)
        result = await service.get_latest_pipeline("main")

        assert result == pipeline
        mock_api.get_latest_pipelines_for_branch.assert_awaited_once_with(
            "gh/org/repo", "main", 1
        )
        assert service.cache_manager.get_latest_pipeline_for_branch("main") == pipeline

    @pytest.mark.asyncio
    async def test_cached(self):
        pipeline = make_pipeline()

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_latest_pipeline_for_branch("main", pipeline)

        result = await service.get_latest_pipeline("main")

        assert result == pipeline
        mock_api.get_latest_pipelines_for_branch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_pipelines_returns_none(self):
        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_latest_pipelines_for_branch.return_value = []

        service = make_service(mock_api)
        result = await service.get_latest_pipeline("main")

        assert result is None

    @pytest.mark.asyncio
    async def test_current_branch(self, monkeypatch):
        pipeline = make_pipeline()

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_latest_pipelines_for_branch.return_value = [pipeline]
        monkeypatch.setattr(
            "circle.service.git.get_current_branch", lambda: "feature-x"
        )

        service = make_service(mock_api)
        result = await service.get_latest_pipeline(CURRENT_BRANCH)

        assert result == pipeline
        mock_api.get_latest_pipelines_for_branch.assert_awaited_once_with(
            "gh/org/repo", "feature-x", 1
        )

    @pytest.mark.asyncio
    async def test_current_branch_not_determined(self, monkeypatch):
        mock_api = create_autospec(api.APIClient, instance=True)
        monkeypatch.setattr("circle.service.git.get_current_branch", lambda: None)

        service = make_service(mock_api)

        with pytest.raises(AppError, match="Current branch could not be determined"):
            await service.get_latest_pipeline(CURRENT_BRANCH)


class TestGetLatestPipelines:
    @pytest.mark.asyncio
    async def test_for_branch_not_cached(self):
        p1 = make_pipeline(id="pipe-1")
        p2 = make_pipeline(id="pipe-2")
        wf1 = [make_workflow(id="wf-1", pipeline_id="pipe-1")]
        wf2 = [make_workflow(id="wf-2", pipeline_id="pipe-2")]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_latest_pipelines_for_branch.return_value = [p1, p2]
        mock_api.get_pipeline_workflows.side_effect = lambda pid: {
            "pipe-1": wf1,
            "pipe-2": wf2,
        }[pid]

        service = make_service(mock_api)
        result = await service.get_latest_pipelines("main", 2)

        assert result == [
            PipelineWithWorkflows(pipeline=p1, workflows=wf1),
            PipelineWithWorkflows(pipeline=p2, workflows=wf2),
        ]
        mock_api.get_latest_pipelines_for_branch.assert_awaited_once_with(
            "gh/org/repo", "main", 2
        )
        assert_awaited_with_args(
            mock_api.get_pipeline_workflows,
            ("pipe-1",),
            ("pipe-2",),
        )
        assert service.cache_manager.get_latest_pipelines_for_branch("main", 2) == [
            p1,
            p2,
        ]

    @pytest.mark.asyncio
    async def test_for_branch_cached(self):
        p1 = make_pipeline(id="pipe-1")
        wf1 = [make_workflow(id="wf-1", pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_latest_pipelines_for_branch("main", 1, [p1])
        service.cache_manager.set_pipeline_workflows("pipe-1", wf1)

        result = await service.get_latest_pipelines("main", 1)

        assert result == [PipelineWithWorkflows(pipeline=p1, workflows=wf1)]
        mock_api.get_latest_pipelines_for_branch.assert_not_awaited()
        mock_api.get_pipeline_workflows.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_any_branch_not_cached(self):
        p1 = make_pipeline(id="pipe-1")
        wf1 = [make_workflow(id="wf-1", pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_my_latest_pipelines.return_value = [p1]
        mock_api.get_pipeline_workflows.return_value = wf1

        service = make_service(mock_api)
        result = await service.get_latest_pipelines(ANY_BRANCH, 1)

        assert result == [PipelineWithWorkflows(pipeline=p1, workflows=wf1)]
        mock_api.get_my_latest_pipelines.assert_awaited_once_with("gh/org/repo", 1)
        mock_api.get_latest_pipelines_for_branch.assert_not_awaited()  # Sanity check
        mock_api.get_pipeline_workflows.assert_awaited_once_with("pipe-1")
        assert service.cache_manager.get_my_latest_pipelines(1) == [p1]

    @pytest.mark.asyncio
    async def test_any_branch_cached(self):
        p1 = make_pipeline(id="pipe-1")
        wf1 = [make_workflow(id="wf-1", pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_my_latest_pipelines(1, [p1])
        service.cache_manager.set_pipeline_workflows("pipe-1", wf1)

        result = await service.get_latest_pipelines(ANY_BRANCH, 1)

        assert result == [PipelineWithWorkflows(pipeline=p1, workflows=wf1)]
        mock_api.get_my_latest_pipelines.assert_not_awaited()
        mock_api.get_latest_pipelines_for_branch.assert_not_awaited()  # Sanity check
        mock_api.get_pipeline_workflows.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_current_branch(self, monkeypatch):
        p1 = make_pipeline(id="pipe-1")
        wf1 = [make_workflow(id="wf-1", pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_latest_pipelines_for_branch.return_value = [p1]
        mock_api.get_pipeline_workflows.return_value = wf1
        monkeypatch.setattr(
            "circle.service.git.get_current_branch", lambda: "feature-x"
        )

        service = make_service(mock_api)
        result = await service.get_latest_pipelines(CURRENT_BRANCH, 1)

        assert result == [PipelineWithWorkflows(pipeline=p1, workflows=wf1)]
        mock_api.get_latest_pipelines_for_branch.assert_awaited_once_with(
            "gh/org/repo", "feature-x", 1
        )


class TestGetPipelineWorkflows:
    @pytest.mark.asyncio
    async def test_not_cached(self):
        workflows = [make_workflow(pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_pipeline_workflows.return_value = workflows

        service = make_service(mock_api)
        result = await service.get_pipeline_workflows("pipe-1")

        assert result == workflows
        mock_api.get_pipeline_workflows.assert_awaited_once_with("pipe-1")
        assert service.cache_manager.get_pipeline_workflows("pipe-1") == workflows

    @pytest.mark.asyncio
    async def test_cached(self):
        workflows = [make_workflow(pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_pipeline_workflows("pipe-1", workflows)

        result = await service.get_pipeline_workflows("pipe-1")

        assert result == workflows
        mock_api.get_pipeline_workflows.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_none_resolves_current_branch(self, monkeypatch):
        pipeline = make_pipeline(id="pipe-1")
        workflows = [make_workflow(pipeline_id="pipe-1")]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_latest_pipelines_for_branch.return_value = [pipeline]
        mock_api.get_pipeline_workflows.return_value = workflows
        monkeypatch.setattr(
            "circle.service.git.get_current_branch", lambda: "feature-x"
        )

        service = make_service(mock_api)
        result = await service.get_pipeline_workflows(None)

        assert result == workflows
        mock_api.get_latest_pipelines_for_branch.assert_awaited_once_with(
            "gh/org/repo", "feature-x", 1
        )
        mock_api.get_pipeline_workflows.assert_awaited_once_with("pipe-1")


class TestGetWorkflowJobs:
    @pytest.mark.asyncio
    async def test_by_pipeline_id(self):
        wf = make_workflow(id="wf-1", pipeline_id="pipe-1")
        job = make_job(id="job-1", status="success")

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_pipeline_workflows.return_value = [wf]
        mock_api.get_workflow_jobs.return_value = [job]

        service = make_service(mock_api)
        result = await service.get_workflow_jobs("pipe-1", None)

        assert result == [
            WorkflowWithJobs(
                workflow=wf,
                jobs=[job],
                job_counts_by_status={api_types.JobStatus.success: 1},
            )
        ]
        mock_api.get_pipeline_workflows.assert_awaited_once_with("pipe-1")
        mock_api.get_workflow_jobs.assert_awaited_once_with("wf-1")
        assert service.cache_manager.get_workflow_jobs("wf-1") == [job]

    @pytest.mark.asyncio
    async def test_by_pipeline_id_cached(self):
        wf = make_workflow(id="wf-1", pipeline_id="pipe-1")
        job = make_job(id="job-1", status="success")

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_pipeline_workflows("pipe-1", [wf])
        service.cache_manager.set_workflow_jobs(
            "wf-1", api_types.WorkflowStatus.success, [job]
        )

        result = await service.get_workflow_jobs("pipe-1", None)

        assert result == [
            WorkflowWithJobs(
                workflow=wf,
                jobs=[job],
                job_counts_by_status={api_types.JobStatus.success: 1},
            )
        ]
        mock_api.get_pipeline_workflows.assert_not_awaited()
        mock_api.get_workflow_jobs.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_by_workflow_ids(self):
        wf1 = make_workflow(id="wf-1", pipeline_id="pipe-1")
        wf2 = make_workflow(id="wf-2", pipeline_id="pipe-1")
        job1 = make_job(id="job-1")
        job2 = make_job(id="job-2")

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_workflow.side_effect = lambda wid: {"wf-1": wf1, "wf-2": wf2}[wid]
        mock_api.get_workflow_jobs.side_effect = lambda wid: {
            "wf-1": [job1],
            "wf-2": [job2],
        }[wid]

        service = make_service(mock_api)
        result = await service.get_workflow_jobs(None, ["wf-1", "wf-2"])

        assert len(result) == 2
        assert result[0].workflow == wf1
        assert result[1].workflow == wf2
        mock_api.get_pipeline_workflows.assert_not_awaited()
        assert service.cache_manager.get_workflow("wf-1") == wf1
        assert service.cache_manager.get_workflow("wf-2") == wf2

    @pytest.mark.asyncio
    async def test_by_workflow_ids_cached(self):
        wf1 = make_workflow(id="wf-1", pipeline_id="pipe-1")
        job1 = make_job(id="job-1", status="success")

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_workflow(wf1)
        service.cache_manager.set_workflow_jobs(
            "wf-1", api_types.WorkflowStatus.success, [job1]
        )

        result = await service.get_workflow_jobs(None, ["wf-1"])

        assert result[0].workflow == wf1
        assert result[0].jobs == [job1]
        mock_api.get_workflow.assert_not_awaited()
        mock_api.get_workflow_jobs.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_workflow_ids_validated_against_pipeline(self):
        wf = make_workflow(id="wf-1", pipeline_id="other-pipe")

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_workflow.return_value = wf
        mock_api.get_workflow_jobs.return_value = []

        service = make_service(mock_api)

        with pytest.raises(AppError, match="does not belong to pipeline"):
            await service.get_workflow_jobs("pipe-1", ["wf-1"])

    @pytest.mark.asyncio
    async def test_no_pipeline_or_workflows_uses_current_branch(self, monkeypatch):
        pipeline = make_pipeline(id="pipe-1")
        wf = make_workflow(id="wf-1", pipeline_id="pipe-1")
        job = make_job(id="job-1", status="success")

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_latest_pipelines_for_branch.return_value = [pipeline]
        mock_api.get_pipeline_workflows.return_value = [wf]
        mock_api.get_workflow_jobs.return_value = [job]
        monkeypatch.setattr(
            "circle.service.git.get_current_branch", lambda: "feature-x"
        )

        service = make_service(mock_api)
        result = await service.get_workflow_jobs(None, None)

        assert len(result) == 1
        assert result[0].workflow == wf
        mock_api.get_latest_pipelines_for_branch.assert_awaited_once_with(
            "gh/org/repo", "feature-x", 1
        )

    @pytest.mark.asyncio
    async def test_status_filter(self):
        wf = make_workflow(id="wf-1", pipeline_id="pipe-1")
        success_job = make_job(id="job-1", status="success")
        failed_job = make_job(id="job-2", status="failed")

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_pipeline_workflows.return_value = [wf]
        mock_api.get_workflow_jobs.return_value = [success_job, failed_job]

        service = make_service(mock_api)
        result = await service.get_workflow_jobs(
            "pipe-1", None, statuses={api_types.JobStatus.failed}
        )

        assert result[0].jobs == [failed_job]
        # Counts reflect all jobs, not just filtered
        assert result[0].job_counts_by_status == {
            api_types.JobStatus.success: 1,
            api_types.JobStatus.failed: 1,
        }


class TestGetJobDetails:
    @pytest.mark.asyncio
    async def test_not_cached(self):
        details = make_job_details(number=42)
        v1_details = make_v1_job_details(
            steps=[
                {
                    "name": "Run tests",
                    "actions": [{"index": 0, "status": "success"}],
                }
            ]
        )

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_job_details.return_value = details
        mock_api.get_v1_job_details.return_value = v1_details

        service = make_service(mock_api)
        result = await service.get_job_details(42)

        assert result.details == details
        assert result.steps_by_action_index == {
            0: [
                StepAction(
                    step_index=0,
                    step=v1_details.steps[0],
                    action=v1_details.steps[0].actions[0],
                )
            ]
        }
        mock_api.get_job_details.assert_awaited_once_with("gh/org/repo", 42)
        mock_api.get_v1_job_details.assert_awaited_once_with("gh/org/repo", 42)
        assert service.cache_manager.get_job_details(42) == details
        assert service.cache_manager.get_v1_job_details(42) == v1_details

    @pytest.mark.asyncio
    async def test_cached(self):
        details = make_job_details(number=42)
        v1_details = make_v1_job_details()

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_job_details(42, details)
        service.cache_manager.set_v1_job_details(42, v1_details)

        result = await service.get_job_details(42)

        assert result.details == details
        mock_api.get_job_details.assert_not_awaited()
        mock_api.get_v1_job_details.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_step_status_filter(self):
        details = make_job_details(number=42)
        v1_details = make_v1_job_details(
            steps=[
                {
                    "name": "Setup",
                    "actions": [{"index": 0, "status": "success"}],
                },
                {
                    "name": "Run tests",
                    "actions": [{"index": 0, "status": "failed"}],
                },
            ]
        )

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_job_details.return_value = details
        mock_api.get_v1_job_details.return_value = v1_details

        service = make_service(mock_api)
        result = await service.get_job_details(42, step_statuses={"failed"})

        assert result.steps_by_action_index == {
            0: [
                StepAction(
                    step_index=1,
                    step=v1_details.steps[1],
                    action=v1_details.steps[1].actions[0],
                )
            ]
        }

    @pytest.mark.asyncio
    async def test_parallel_steps_grouped_by_action_index(self):
        details = make_job_details(number=42, parallelism=2)
        v1_details = make_v1_job_details(
            steps=[
                {
                    "name": "Run tests",
                    "actions": [
                        {"index": 0, "status": "success"},
                        {"index": 1, "status": "failed"},
                    ],
                },
            ]
        )

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_job_details.return_value = details
        mock_api.get_v1_job_details.return_value = v1_details

        service = make_service(mock_api)
        result = await service.get_job_details(42)

        assert result.steps_by_action_index == {
            0: [
                StepAction(
                    step_index=0,
                    step=v1_details.steps[0],
                    action=v1_details.steps[0].actions[0],
                )
            ],
            1: [
                StepAction(
                    step_index=0,
                    step=v1_details.steps[0],
                    action=v1_details.steps[0].actions[1],
                )
            ],
        }


class TestGetJobOutput:
    @pytest.mark.asyncio
    async def test_not_cached(self):
        output = [make_job_output_message()]
        v1_details = make_v1_job_details(
            steps=[
                {
                    "name": "Run tests",
                    "actions": [
                        {
                            "index": 0,
                            "status": "success",
                            "output_url": "https://output",
                        },
                    ],
                }
            ]
        )

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_v1_job_details.return_value = v1_details
        mock_api.get_job_output.return_value = output

        service = make_service(mock_api)
        result = await service.get_job_output(42, step=0, parallel_index=0)

        assert result == output
        mock_api.get_v1_job_details.assert_awaited_once_with("gh/org/repo", 42)
        mock_api.get_job_output.assert_awaited_once_with("https://output")
        assert service.cache_manager.get_job_output(42, 0, 0) == output

    @pytest.mark.asyncio
    async def test_cached(self):
        output = [make_job_output_message()]

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_job_output(
            42, api_types.V1JobLifecycle.finished, 0, 0, output
        )

        result = await service.get_job_output(42, step=0, parallel_index=0)

        assert result == output
        mock_api.get_v1_job_details.assert_not_awaited()
        mock_api.get_job_output.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_none_parallel_index_defaults_to_zero(self):
        details = make_job_details(number=42, parallelism=1)
        v1_details = make_v1_job_details(
            steps=[
                {
                    "name": "Run tests",
                    "actions": [
                        {
                            "index": 0,
                            "status": "success",
                            "output_url": "https://output",
                        },
                    ],
                }
            ]
        )
        output = [make_job_output_message()]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_job_details.return_value = details
        mock_api.get_v1_job_details.return_value = v1_details
        mock_api.get_job_output.return_value = output

        service = make_service(mock_api)
        result = await service.get_job_output(42, step=0, parallel_index=None)

        assert result == output

    @pytest.mark.asyncio
    async def test_none_parallel_index_raises_for_parallel_jobs(self):
        details = make_job_details(number=42, parallelism=2)
        v1_details = make_v1_job_details()

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_job_details.return_value = details
        mock_api.get_v1_job_details.return_value = v1_details

        service = make_service(mock_api)

        with pytest.raises(AppError, match="parallel index is required"):
            await service.get_job_output(42, step=0, parallel_index=None)

    @pytest.mark.asyncio
    async def test_invalid_step_raises(self):
        v1_details = make_v1_job_details(steps=[])

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_v1_job_details.return_value = v1_details

        service = make_service(mock_api)

        with pytest.raises(AppError, match=r"No steps matching filter \(step=0\)"):
            await service.get_job_output(42, step=0, parallel_index=0)

    @pytest.mark.asyncio
    async def test_invalid_parallel_index_raises(self):
        v1_details = make_v1_job_details(
            steps=[
                {
                    "name": "Run tests",
                    "actions": [{"index": 0, "status": "success"}],
                }
            ]
        )

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_v1_job_details.return_value = v1_details

        service = make_service(mock_api)

        with pytest.raises(
            AppError, match=r"No steps matching filter \(parallel_index=5\)"
        ):
            await service.get_job_output(42, step=0, parallel_index=5)

    @pytest.mark.asyncio
    async def test_no_output_url_raises(self):
        v1_details = make_v1_job_details(
            steps=[
                {
                    "name": "Run tests",
                    "actions": [{"index": 0, "status": "success", "output_url": None}],
                }
            ]
        )

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_v1_job_details.return_value = v1_details

        service = make_service(mock_api)

        with pytest.raises(AppError, match="Output URL not found"):
            await service.get_job_output(42, step=0, parallel_index=0)


class TestGetJobTests:
    @pytest.mark.asyncio
    async def test_not_cached(self):
        details = make_job_details(number=42)
        tests = [make_job_test()]

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_job_details.return_value = details
        mock_api.get_job_tests.return_value = tests

        service = make_service(mock_api)
        result = await service.get_job_tests(42)

        assert result == tests
        mock_api.get_job_details.assert_awaited_once_with("gh/org/repo", 42)
        mock_api.get_job_tests.assert_awaited_once_with("gh/org/repo", 42)
        assert service.cache_manager.get_job_tests(42) == tests

    @pytest.mark.asyncio
    async def test_cached(self):
        tests = [make_job_test()]

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_job_tests(42, api_types.JobStatus.success, tests)

        result = await service.get_job_tests(42)

        assert result == tests
        mock_api.get_job_details.assert_not_awaited()
        mock_api.get_job_tests.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_filter_by_status(self):
        success_test = make_job_test(name="test_a", result="success")
        failure_test = make_job_test(name="test_b", result="failure")

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_job_tests(
            42, api_types.JobStatus.success, [success_test, failure_test]
        )

        result = await service.get_job_tests(
            42, statuses={api_types.JobTestResult.failure}
        )

        assert result == [failure_test]

    @pytest.mark.asyncio
    async def test_filter_by_file_suffix(self):
        py_test = make_job_test(name="test_a", file="tests/test_foo.py")
        js_test = make_job_test(name="test_b", file="tests/test_bar.js")

        mock_api = create_autospec(api.APIClient, instance=True)

        service = make_service(mock_api)
        service.cache_manager.set_job_tests(
            42, api_types.JobStatus.success, [py_test, js_test]
        )

        result = await service.get_job_tests(42, file_suffix=".py")

        assert result == [py_test]


class TestGetWorkflowFailedTests:
    @pytest.mark.asyncio
    async def test_collects_failed_tests_across_jobs(self):
        wf = make_workflow(id="wf-1", pipeline_id="pipe-1", status="failed")
        job1 = make_job(id="job-1", job_number=10, name="test-a", status="failed")
        job2 = make_job(id="job-2", job_number=11, name="test-b", status="failed")
        details1 = make_job_details(number=10)
        details2 = make_job_details(number=11)

        failure1 = make_job_test(
            name="test_x",
            classname="tests.test_foo",
            file="tests/test_foo.py",
            result="failure",
        )
        failure2 = make_job_test(
            name="test_y",
            classname="tests.test_bar",
            file="tests/test_bar.py",
            result="failure",
        )
        success_test = make_job_test(name="test_z", result="success")

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_workflow.return_value = wf
        mock_api.get_workflow_jobs.return_value = [job1, job2]
        mock_api.get_job_details.side_effect = lambda slug, num: {
            10: details1,
            11: details2,
        }[num]
        mock_api.get_job_tests.side_effect = lambda slug, num: {
            10: [failure1, success_test],
            11: [failure2],
        }[num]

        service = make_service(mock_api)
        results = await service.get_failed_tests(None, ["wf-1"])

        assert len(results) == 1
        assert results[0].workflow == wf
        assert results[0].failed_tests == {
            "tests/test_foo.py": {
                "tests.test_foo": {
                    "test_x": [FailedTestJobInfo(job_number=10, job_name="test-a")],
                },
            },
            "tests/test_bar.py": {
                "tests.test_bar": {
                    "test_y": [FailedTestJobInfo(job_number=11, job_name="test-b")],
                },
            },
        }

    @pytest.mark.asyncio
    async def test_same_test_failing_in_multiple_jobs(self):
        wf = make_workflow(id="wf-1", pipeline_id="pipe-1", status="failed")
        job1 = make_job(id="job-1", job_number=10, name="test-a", status="failed")
        job2 = make_job(id="job-2", job_number=11, name="test-b", status="failed")
        details1 = make_job_details(number=10)
        details2 = make_job_details(number=11)

        shared_failure = make_job_test(
            name="test_x",
            classname="tests.test_foo",
            file="tests/test_foo.py",
            result="failure",
        )

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_workflow.return_value = wf
        mock_api.get_workflow_jobs.return_value = [job1, job2]
        mock_api.get_job_details.side_effect = lambda slug, num: {
            10: details1,
            11: details2,
        }[num]
        mock_api.get_job_tests.side_effect = lambda slug, num: {
            10: [shared_failure],
            11: [shared_failure],
        }[num]

        service = make_service(mock_api)
        results = await service.get_failed_tests(None, ["wf-1"])

        assert len(results) == 1
        job_infos = results[0].failed_tests["tests/test_foo.py"]["tests.test_foo"][
            "test_x"
        ]
        assert len(job_infos) == 2
        assert job_infos == [
            FailedTestJobInfo(job_number=10, job_name="test-a"),
            FailedTestJobInfo(job_number=11, job_name="test-b"),
        ]

    @pytest.mark.asyncio
    async def test_no_failed_tests(self):
        wf = make_workflow(id="wf-1", pipeline_id="pipe-1", status="failed")
        job = make_job(id="job-1", job_number=10, name="test-a", status="failed")
        details = make_job_details(number=10)
        success_test = make_job_test(name="test_z", result="success")

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_workflow.return_value = wf
        mock_api.get_workflow_jobs.return_value = [job]
        mock_api.get_job_details.return_value = details
        mock_api.get_job_tests.return_value = [success_test]

        service = make_service(mock_api)
        results = await service.get_failed_tests(None, ["wf-1"])

        assert len(results) == 1
        assert results[0].workflow == wf
        assert results[0].failed_tests == {}

    @pytest.mark.asyncio
    async def test_no_failed_jobs(self):
        wf = make_workflow(id="wf-1", pipeline_id="pipe-1", status="failed")

        mock_api = create_autospec(api.APIClient, instance=True)
        mock_api.get_workflow.return_value = wf
        mock_api.get_workflow_jobs.return_value = []

        service = make_service(mock_api)
        results = await service.get_failed_tests(None, ["wf-1"])

        assert len(results) == 1
        assert results[0].workflow == wf
        assert results[0].failed_tests == {}
