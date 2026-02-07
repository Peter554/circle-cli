from __future__ import annotations

from datetime import datetime, timedelta, timezone

from circle import api_types


def _deep_merge(base: dict, overrides: dict) -> dict:
    result = base.copy()
    for k, v in overrides.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


PIPELINE_CREATED_AT = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_pipeline(**overrides) -> api_types.Pipeline:
    defaults = dict(
        id="pipe-1",
        number=1,
        project_slug="gh/org/repo",
        created_at=PIPELINE_CREATED_AT,
        errors=[],
        state="created",
        trigger=dict(
            type="webhook",
            received_at=PIPELINE_CREATED_AT,
            actor=dict(login="user", avatar_url=None),
        ),
    )
    return api_types.Pipeline(**_deep_merge(defaults, overrides))


def make_workflow(**overrides) -> api_types.Workflow:
    defaults = dict(
        id="wf-1",
        name="build",
        status="success",
        created_at=PIPELINE_CREATED_AT,
        stopped_at=PIPELINE_CREATED_AT + timedelta(minutes=1),
        pipeline_id="pipe-1",
        pipeline_number=1,
        project_slug="gh/org/repo",
        started_by="user-1",
    )
    return api_types.Workflow(**_deep_merge(defaults, overrides))


def make_job(**overrides) -> api_types.Job:
    defaults = dict(
        id="job-1",
        name="test",
        dependencies=[],
        project_slug="gh/org/repo",
        status="success",
        type="build",
        job_number=42,
    )
    return api_types.Job(**_deep_merge(defaults, overrides))


def make_job_details(**overrides) -> api_types.JobDetails:
    defaults = dict(
        web_url="https://circleci.com/job/1",
        project=dict(
            id="proj-1",
            slug="gh/org/repo",
            name="repo",
            external_url="https://example.com",
        ),
        parallel_runs=[dict(index=0, status="success")],
        started_at=PIPELINE_CREATED_AT,
        latest_workflow=dict(id="wf-1", name="build"),
        name="test",
        executor=dict(resource_class="medium"),
        parallelism=1,
        status="success",
        number=42,
        pipeline=dict(id="pipe-1"),
        duration=60,
        created_at=PIPELINE_CREATED_AT,
        messages=[],
        contexts=[],
        organization=dict(name="org"),
        queued_at=PIPELINE_CREATED_AT,
        stopped_at=PIPELINE_CREATED_AT + timedelta(minutes=1),
    )
    return api_types.JobDetails(**_deep_merge(defaults, overrides))


def make_v1_job_details(**overrides) -> api_types.V1JobDetails:
    defaults = dict(
        status="success",
        lifecycle="finished",
    )
    return api_types.V1JobDetails(**_deep_merge(defaults, overrides))


def make_job_test(**overrides) -> api_types.JobTestMetadata:
    defaults = dict(
        name="test_one",
        classname="tests.test_foo",
        file="tests/test_foo.py",
        result="success",
        run_time=0.1,
        message=None,
        source="pytest",
    )
    return api_types.JobTestMetadata(**_deep_merge(defaults, overrides))


def make_job_output_message(**overrides) -> api_types.JobOutputMessage:
    defaults = dict(
        message="hello",
        time=PIPELINE_CREATED_AT + timedelta(minutes=1),
        truncated=False,
        type="out",
    )
    return api_types.JobOutputMessage(**_deep_merge(defaults, overrides))
