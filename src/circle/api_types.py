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


class JobDetails(BaseModel):
    web_url: str
    project: JobProject
    parallel_runs: list[ParallelRun]
    started_at: datetime.datetime
    latest_workflow: LatestWorkflow
    name: str
    executor: Executor
    parallelism: int
    status: JobStatus
    number: int
    pipeline: JobPipeline
    duration: int | None
    created_at: datetime.datetime
    messages: list[JobMessage]
    contexts: list[JobContext]
    organization: JobOrganization
    queued_at: datetime.datetime
    stopped_at: datetime.datetime | None


class JobProject(BaseModel):
    id: str
    slug: str
    name: str
    external_url: str


class ParallelRun(BaseModel):
    index: int
    status: str


class LatestWorkflow(BaseModel):
    id: str
    name: str


class Executor(BaseModel):
    resource_class: str
    type: str | None = None


class JobPipeline(BaseModel):
    id: str


class JobMessage(BaseModel):
    type: str
    message: str
    reason: str | None = None


class JobContext(BaseModel):
    name: str


class JobOrganization(BaseModel):
    name: str


class V1JobDetails(BaseModel):
    status: V1JobStatus
    lifecycle: V1JobLifecycle
    outcome: V1JobOutcome | None = None
    steps: list[V1JobStep] = pydantic.Field(default_factory=list)


class V1JobStatus(enum.StrEnum):
    retried = "retried"
    canceled = "canceled"
    infrastructure_fail = "infrastructure_fail"
    timedout = "timedout"
    not_run = "not_run"
    running = "running"
    failed = "failed"
    queued = "queued"
    not_running = "not_running"
    no_tests = "no_tests"
    fixed = "fixed"
    success = "success"


class V1JobAction(BaseModel):
    index: int
    status: str  # Unsure of enum here (spec unclear)
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    output_url: str | None = None


class V1JobOutcome(enum.StrEnum):
    canceled = "canceled"
    infrastructure_fail = "infrastructure_fail"
    timedout = "timedout"
    failed = "failed"
    no_tests = "no_tests"
    success = "success"


class V1JobLifecycle(enum.StrEnum):
    queued = "queued"
    not_run = "not_run"
    not_running = "not_running"
    running = "running"
    finished = "finished"


class V1JobStep(BaseModel):
    name: str
    actions: list[V1JobAction]


class JobOutputMessage(BaseModel):
    message: str
    time: datetime.datetime
    truncated: bool
    type: str


type JobOutput = list[JobOutputMessage]
