from datetime import datetime, timedelta, timezone

import pytest
import time_machine

from circle import api_types
from circle.cache_manager import CacheManager
from tests.conftest import (
    FakeCache,
    PIPELINE_CREATED_AT,
    make_job,
    make_job_details,
    make_job_output_message,
    make_job_test,
    make_pipeline,
    make_v1_job_details,
    make_workflow,
)


FINISHED_WORKFLOW_STATUSES = {
    api_types.WorkflowStatus.success,
    api_types.WorkflowStatus.failed,
    api_types.WorkflowStatus.error,
    api_types.WorkflowStatus.canceled,
    api_types.WorkflowStatus.unauthorized,
}

IN_PROGRESS_WORKFLOW_STATUSES = (
    set(api_types.WorkflowStatus) - FINISHED_WORKFLOW_STATUSES
)

FINISHED_JOB_STATUSES = {
    api_types.JobStatus.success,
    api_types.JobStatus.failed,
    api_types.JobStatus.canceled,
    api_types.JobStatus.unauthorized,
    api_types.JobStatus.not_run,
}

IN_PROGRESS_JOB_STATUSES = set(api_types.JobStatus) - FINISHED_JOB_STATUSES

FINISHED_V1_LIFECYCLES = {api_types.V1JobLifecycle.finished}

IN_PROGRESS_V1_LIFECYCLES = set(api_types.V1JobLifecycle) - FINISHED_V1_LIFECYCLES


class TestMyLatestPipelines:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        pipelines = [make_pipeline()]

        assert cm.get_my_latest_pipelines(5) is None
        cm.set_my_latest_pipelines(5, pipelines)
        assert cm.get_my_latest_pipelines(5) == pipelines

    def test_ttl_is_always_in_progress(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_my_latest_pipelines(5, [make_pipeline()])
        assert spy.ttls["latest_pipelines:mine:5"] == cm.in_progress_ttl_seconds


class TestLatestPipelineForBranch:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        pipeline = make_pipeline()

        assert cm.get_latest_pipeline_for_branch("main") is None
        cm.set_latest_pipeline_for_branch("main", pipeline)
        assert cm.get_latest_pipeline_for_branch("main") == pipeline

    def test_ttl_is_always_in_progress(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_latest_pipeline_for_branch("main", make_pipeline())
        assert spy.ttls["latest_pipeline:branch:main"] == cm.in_progress_ttl_seconds


class TestLatestPipelinesForBranch:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        pipelines = [make_pipeline()]

        assert cm.get_latest_pipelines_for_branch("main", 3) is None
        cm.set_latest_pipelines_for_branch("main", 3, pipelines)
        assert cm.get_latest_pipelines_for_branch("main", 3) == pipelines

    def test_also_sets_latest_pipeline_for_branch(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        pipelines = [make_pipeline(id="first"), make_pipeline(id="second")]

        cm.set_latest_pipelines_for_branch("main", 2, pipelines)
        assert cm.get_latest_pipeline_for_branch("main") == pipelines[0]

    def test_ttl_is_always_in_progress(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_latest_pipelines_for_branch("main", 3, [make_pipeline()])
        assert spy.ttls["latest_pipelines:branch:main:3"] == cm.in_progress_ttl_seconds


class TestPipelineIdByNumber:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)

        assert cm.get_pipeline_id_by_number(10) is None
        cm.set_pipeline_id_by_number(10, "pipe-abc")
        assert cm.get_pipeline_id_by_number(10) == "pipe-abc"

    def test_ttl_is_always_finished(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_pipeline_id_by_number(10, "pipe-abc")
        assert spy.ttls["pipeline_id_by_number:10"] == cm.finished_ttl_seconds


class TestPipeline:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        pipeline = make_pipeline()

        assert cm.get_pipeline(pipeline.id) is None
        cm.set_pipeline(pipeline)
        assert cm.get_pipeline(pipeline.id) == pipeline

    def test_ttl_is_always_in_progress(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_pipeline(make_pipeline())
        assert spy.ttls["pipeline:pipe-1"] == cm.in_progress_ttl_seconds


class TestWorkflow:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        wf = make_workflow()

        assert cm.get_workflow(wf.id) is None
        cm.set_workflow(wf)
        assert cm.get_workflow(wf.id) == wf

    @pytest.mark.parametrize("status", FINISHED_WORKFLOW_STATUSES)
    def test_finished_workflow_gets_long_ttl(self, status):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_workflow(make_workflow(status=status))
        assert spy.ttls["workflow:wf-1"] == cm.finished_ttl_seconds

    @pytest.mark.parametrize("status", IN_PROGRESS_WORKFLOW_STATUSES)
    def test_in_progress_workflow_gets_short_ttl(self, status):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_workflow(make_workflow(status=status))
        assert spy.ttls["workflow:wf-1"] == cm.in_progress_ttl_seconds


class TestPipelineWorkflows:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        workflows = [make_workflow()]

        assert cm.get_pipeline_workflows("pipe-1") is None
        cm.set_pipeline_workflows("pipe-1", workflows)
        assert cm.get_pipeline_workflows("pipe-1") == workflows

    def test_also_sets_individual_workflows(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        wf = make_workflow()

        cm.set_pipeline_workflows("pipe-1", [wf])
        assert cm.get_workflow(wf.id) == wf

    @time_machine.travel(PIPELINE_CREATED_AT + timedelta(minutes=10))
    def test_stopped_over_one_minute_ago_gets_long_ttl(self):
        now = datetime.now(timezone.utc)
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_pipeline_workflows(
            "pipe-1",
            [make_workflow(stopped_at=now - timedelta(minutes=1))],
        )
        assert spy.ttls["pipeline:pipe-1:workflows"] == cm.finished_ttl_seconds

    @time_machine.travel(PIPELINE_CREATED_AT + timedelta(minutes=10))
    def test_stopped_under_one_minute_ago_gets_short_ttl(self):
        now = datetime.now(timezone.utc)
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_pipeline_workflows(
            "pipe-1",
            [make_workflow(stopped_at=now - timedelta(seconds=59))],
        )
        assert spy.ttls["pipeline:pipe-1:workflows"] == cm.in_progress_ttl_seconds

    def test_running_workflow_gets_short_ttl(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_pipeline_workflows(
            "pipe-1", [make_workflow(status="running", stopped_at=None)]
        )
        assert spy.ttls["pipeline:pipe-1:workflows"] == cm.in_progress_ttl_seconds

    @time_machine.travel(PIPELINE_CREATED_AT + timedelta(minutes=10))
    def test_mixed_old_and_recent_stop_times_gets_short_ttl(self):
        now = datetime.now(timezone.utc)
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_pipeline_workflows(
            "pipe-1",
            [
                make_workflow(
                    id="wf-1",
                    stopped_at=now - timedelta(seconds=59),
                ),
                make_workflow(
                    id="wf-2",
                    stopped_at=now - timedelta(minutes=3),
                ),
            ],
        )
        assert spy.ttls["pipeline:pipe-1:workflows"] == cm.in_progress_ttl_seconds

    def test_empty_workflows_gets_short_ttl(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_pipeline_workflows("pipe-1", [])
        assert spy.ttls["pipeline:pipe-1:workflows"] == cm.in_progress_ttl_seconds


class TestWorkflowJobs:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        jobs = [make_job()]

        assert cm.get_workflow_jobs("wf-1") is None
        cm.set_workflow_jobs("wf-1", api_types.WorkflowStatus.success, jobs)
        assert cm.get_workflow_jobs("wf-1") == jobs

    @pytest.mark.parametrize("status", FINISHED_WORKFLOW_STATUSES)
    def test_finished_workflow_gets_long_ttl(self, status):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_workflow_jobs("wf-1", status, [])
        assert spy.ttls["workflow:wf-1:jobs"] == cm.finished_ttl_seconds

    @pytest.mark.parametrize("status", IN_PROGRESS_WORKFLOW_STATUSES)
    def test_in_progress_workflow_gets_short_ttl(self, status):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_workflow_jobs("wf-1", status, [])
        assert spy.ttls["workflow:wf-1:jobs"] == cm.in_progress_ttl_seconds


class TestJobDetails:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        details = make_job_details()

        assert cm.get_job_details(42) is None
        cm.set_job_details(42, details)
        assert cm.get_job_details(42) == details

    @pytest.mark.parametrize("status", FINISHED_JOB_STATUSES)
    def test_finished_job_gets_long_ttl(self, status):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_job_details(42, make_job_details(status=status))
        assert spy.ttls["job_details:42"] == cm.finished_ttl_seconds

    @pytest.mark.parametrize("status", IN_PROGRESS_JOB_STATUSES)
    def test_in_progress_job_gets_short_ttl(self, status):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_job_details(42, make_job_details(status=status))
        assert spy.ttls["job_details:42"] == cm.in_progress_ttl_seconds


class TestV1JobDetails:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        details = make_v1_job_details()

        assert cm.get_v1_job_details(42) is None
        cm.set_v1_job_details(42, details)
        assert cm.get_v1_job_details(42) == details

    @pytest.mark.parametrize("lifecycle", FINISHED_V1_LIFECYCLES)
    def test_finished_gets_long_ttl(self, lifecycle):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_v1_job_details(42, make_v1_job_details(lifecycle=lifecycle))
        assert spy.ttls["v1_job_details:42"] == cm.finished_ttl_seconds

    @pytest.mark.parametrize("lifecycle", IN_PROGRESS_V1_LIFECYCLES)
    def test_in_progress_gets_short_ttl(self, lifecycle):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_v1_job_details(42, make_v1_job_details(lifecycle=lifecycle))
        assert spy.ttls["v1_job_details:42"] == cm.in_progress_ttl_seconds


class TestJobOutput:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        output = [make_job_output_message()]

        assert cm.get_job_output(42, 0, 0) is None
        cm.set_job_output(42, api_types.V1JobLifecycle.finished, 0, 0, output)
        assert cm.get_job_output(42, 0, 0) == output

    @pytest.mark.parametrize("lifecycle", FINISHED_V1_LIFECYCLES)
    def test_finished_gets_long_ttl(self, lifecycle):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_job_output(42, lifecycle, 0, 0, [make_job_output_message()])
        assert spy.ttls["job_output:42:0:0"] == cm.finished_ttl_seconds

    @pytest.mark.parametrize("lifecycle", IN_PROGRESS_V1_LIFECYCLES)
    def test_in_progress_gets_short_ttl(self, lifecycle):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_job_output(42, lifecycle, 0, 0, [make_job_output_message()])
        assert spy.ttls["job_output:42:0:0"] == cm.in_progress_ttl_seconds


class TestJobTests:
    def test_roundtrip(self):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        tests = [make_job_test()]

        assert cm.get_job_tests(42) is None
        cm.set_job_tests(42, api_types.JobStatus.success, tests)
        assert cm.get_job_tests(42) == tests

    @pytest.mark.parametrize("status", FINISHED_JOB_STATUSES)
    def test_finished_job_gets_long_ttl(self, status):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_job_tests(42, status, [])
        assert spy.ttls["job_tests:42"] == cm.finished_ttl_seconds

    @pytest.mark.parametrize("status", IN_PROGRESS_JOB_STATUSES)
    def test_in_progress_job_gets_short_ttl(self, status):
        spy = FakeCache()
        cm = CacheManager(cache=spy)
        cm.set_job_tests(42, status, [])
        assert spy.ttls["job_tests:42"] == cm.in_progress_ttl_seconds
