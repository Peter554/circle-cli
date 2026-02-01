from __future__ import annotations

import datetime
import enum

import pydantic


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore")


class Pipeline(BaseModel):
    id: str
    number: int
    project_slug: str
    created_at: datetime.datetime
    errors: list[PipelineError]
    state: PipelineState
    updated_at: datetime.datetime | None = None
    vcs: VCS | None = None
    trigger: PipelineTrigger
    trigger_parameters: dict | None = None


class PipelineState(enum.StrEnum):
    created = "created"
    errored = "errored"
    setup_pending = "setup-pending"
    setup = "setup"
    pending = "pending"


class PipelineTriggerType(enum.StrEnum):
    scheduled_pipeline = "scheduled_pipeline"
    explicit = "explicit"
    api = "api"
    webhook = "webhook"


class PipelineTrigger(BaseModel):
    type: PipelineTriggerType
    received_at: datetime.datetime
    actor: Actor


class Actor(BaseModel):
    login: str
    avatar_url: str | None


class VCS(BaseModel):
    provider_name: str
    origin_repository_url: str
    target_repository_url: str
    revision: str
    commit: VCSCommit | None = None
    branch: str | None = None
    tag: str | None = None
    review_id: str | None = None
    review_url: str | None = None


class VCSCommit(BaseModel):
    subject: str | None
    body: str | None


class PipelineError(BaseModel):
    type: PipelineErrorType
    message: str


class PipelineErrorType(enum.StrEnum):
    config = "config"
    invalid_trigger_setup = "invalid-trigger-setup"
    config_fetch = "config-fetch"
    timeout = "timeout"
    permission = "permission"
    other = "other"
    trigger_rule = "trigger-rule"
    plan = "plan"


class Workflow(BaseModel):
    id: str
    name: str
    status: WorkflowStatus
    created_at: datetime.datetime
    stopped_at: datetime.datetime | None
    pipeline_id: str
    pipeline_number: int
    project_slug: str
    started_by: str
    canceled_by: str | None = None
    errored_by: str | None = None
    tag: str | None = None
    auto_rerun_number: int | None = None
    max_auto_reruns: int | None = None


class WorkflowStatus(enum.StrEnum):
    success = "success"
    running = "running"
    not_run = "not_run"
    failed = "failed"
    error = "error"
    failing = "failing"
    on_hold = "on_hold"
    canceled = "canceled"
    unauthorized = "unauthorized"


class Job(BaseModel):
    id: str
    name: str
    dependencies: list[str]
    project_slug: str
    status: JobStatus
    type: JobType
    job_number: int | None = None
    started_at: datetime.datetime | None = None
    stopped_at: datetime.datetime | None = None
    canceled_by: str | None = None
    approved_by: str | None = None
    approval_request_id: str | None = None
    requires: dict[str, list[str]] | None = None


class JobStatus(enum.StrEnum):
    success = "success"
    running = "running"
    not_run = "not_run"
    failed = "failed"
    retried = "retried"
    queued = "queued"
    not_running = "not_running"
    infrastructure_fail = "infrastructure_fail"
    timedout = "timedout"
    on_hold = "on_hold"
    terminated_unknown = "terminated-unknown"
    blocked = "blocked"
    canceled = "canceled"
    unauthorized = "unauthorized"


class JobType(enum.StrEnum):
    build = "build"
    approval = "approval"
