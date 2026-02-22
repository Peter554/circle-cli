from __future__ import annotations

import asyncio
import dataclasses
import typing
from collections import Counter, defaultdict
from collections.abc import Container

import pydantic

from . import api, api_types, cache_manager, git

CURRENT_BRANCH: typing.Final = "@current"
ANY_BRANCH: typing.Final = "@any"


class AppError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class AppService:
    project_slug: str
    api_client: api.APIClient
    cache_manager: cache_manager.CacheManager

    async def get_pipeline(self, pipeline_id_or_number: str) -> PipelineWithWorkflows:
        pipeline_id = await self._resolve_pipeline_id(pipeline_id_or_number)

        pipeline = self.cache_manager.get_pipeline(pipeline_id)
        if pipeline is None:
            pipeline = await self.api_client.get_pipeline_by_id(pipeline_id)
            self.cache_manager.set_pipeline(pipeline)

        workflows = await self.get_pipeline_workflows(pipeline.id)

        return PipelineWithWorkflows(pipeline=pipeline, workflows=workflows)

    async def _resolve_pipeline_id(self, pipeline_id_or_number: str) -> str:
        if not pipeline_id_or_number.isdigit():
            return pipeline_id_or_number

        pipeline_number = int(pipeline_id_or_number)
        pipeline_id = self.cache_manager.get_pipeline_id_by_number(pipeline_number)
        if pipeline_id is None:
            pipeline = await self.api_client.get_pipeline_by_number(
                self.project_slug, pipeline_number
            )
            self.cache_manager.set_pipeline_id_by_number(pipeline_number, pipeline.id)
            self.cache_manager.set_pipeline(pipeline)
            pipeline_id = pipeline.id

        return pipeline_id

    async def get_latest_pipeline(
        self,
        branch: str,
    ) -> api_types.Pipeline | None:
        branch = self._get_branch(branch)

        pipeline = self.cache_manager.get_latest_pipeline_for_branch(branch)
        if pipeline is None:
            pipelines = await self.api_client.get_latest_pipelines_for_branch(
                self.project_slug, branch, 1
            )
            pipeline = pipelines[0] if pipelines else None
            self.cache_manager.set_latest_pipeline_for_branch(branch, pipeline)

        return pipeline

    async def get_latest_pipelines(
        self,
        branch: str,
        n: int,
    ) -> list[PipelineWithWorkflows]:
        branch = self._get_branch(branch)

        if branch == ANY_BRANCH:
            pipelines = self.cache_manager.get_my_latest_pipelines(n)
            if pipelines is None:
                pipelines = await self.api_client.get_my_latest_pipelines(
                    self.project_slug, n
                )
                self.cache_manager.set_my_latest_pipelines(n, pipelines)
        else:
            pipelines = self.cache_manager.get_latest_pipelines_for_branch(branch, n)
            if pipelines is None:
                pipelines = await self.api_client.get_latest_pipelines_for_branch(
                    self.project_slug, branch, n
                )
                self.cache_manager.set_latest_pipelines_for_branch(branch, n, pipelines)

        # Fetch workflows for all pipelines concurrently
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self.get_pipeline_workflows(pipeline.id))
                for pipeline in pipelines
            ]
        workflows_lists = [task.result() for task in tasks]

        # Pair pipelines with their workflows
        return [
            PipelineWithWorkflows(pipeline=pipeline, workflows=workflows)
            for pipeline, workflows in zip(pipelines, workflows_lists)
        ]

    async def get_pipeline_workflows(
        self,
        pipeline_id: str | None,
    ) -> list[api_types.Workflow]:
        # If no pipeline ID provided, get the latest pipeline for current branch
        if pipeline_id is None:
            pipeline_id = (await self._get_latest_pipeline_for_current_branch()).id

        workflows = self.cache_manager.get_pipeline_workflows(pipeline_id)
        if workflows is None:
            workflows = await self.api_client.get_pipeline_workflows(pipeline_id)
            self.cache_manager.set_pipeline_workflows(pipeline_id, workflows)

        return workflows

    async def get_workflow_jobs(
        self,
        pipeline_id_or_number: str | None,
        workflow_ids: list[str] | None,
        statuses: Container[api_types.JobStatus] | None = None,
    ) -> list[WorkflowWithJobs]:
        # If workflow IDs are provided use those. If pipeline ID was provided validate it against the workflows.
        # If no workflow IDs are, use workflows for the pipeline ID or latest pipeline for the current branch.

        pipeline_id = (
            await self._resolve_pipeline_id(pipeline_id_or_number)
            if pipeline_id_or_number is not None
            else None
        )

        if workflow_ids:
            # Fetch all workflows concurrently
            async with asyncio.TaskGroup() as tg:
                tasks = [
                    tg.create_task(self._get_workflow(wid)) for wid in workflow_ids
                ]
            workflows = [task.result() for task in tasks]
        else:
            if pipeline_id is None:
                pipeline_id = (await self._get_latest_pipeline_for_current_branch()).id
            workflows = await self.get_pipeline_workflows(pipeline_id)

        # Validate pipeline_id if provided
        if pipeline_id is not None:
            for workflow in workflows:
                if workflow.pipeline_id != pipeline_id:
                    raise AppError(
                        f"Workflow {workflow.id} does not belong to pipeline {pipeline_id}"
                    )

        # Fetch jobs for all workflows concurrently
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self._get_workflow_jobs(workflow))
                for workflow in workflows
            ]
        jobs_lists = [task.result() for task in tasks]

        # Count jobs by status before filtering
        counts_lists = [_count_jobs_by_status(jobs) for jobs in jobs_lists]

        # Filter jobs by status if specified
        if statuses is not None:
            jobs_lists = [
                [job for job in jobs if job.status in statuses] for jobs in jobs_lists
            ]

        # Pair workflows with their jobs
        return [
            WorkflowWithJobs(workflow=workflow, jobs=jobs, job_counts_by_status=counts)
            for workflow, jobs, counts in zip(workflows, jobs_lists, counts_lists)
        ]

    async def get_job_details(
        self, job_number: int, step_statuses: Container[str] | None = None
    ) -> JobDetailsWithSteps:
        # Fetch both details concurrently
        async with asyncio.TaskGroup() as tg:
            v2_task = tg.create_task(self._get_job_details(job_number))
            v1_task = tg.create_task(self._get_v1_job_details(job_number))

        details = v2_task.result()
        v1_details = v1_task.result()

        # Group steps by action index (parallel run)
        steps_by_action_index: dict[int, list[StepAction]] = defaultdict(list)
        for step_idx, step in enumerate(v1_details.steps):
            for action in step.actions:
                steps_by_action_index[action.index].append(
                    StepAction(step_index=step_idx, step=step, action=action)
                )

        # Filter by status if specified
        if step_statuses is not None:
            steps_by_action_index = {
                action_index: [
                    step_action
                    for step_action in step_actions
                    if step_action.action.status in step_statuses
                ]
                for action_index, step_actions in steps_by_action_index.items()
            }

        return JobDetailsWithSteps(
            details=details, steps_by_action_index=steps_by_action_index
        )

    async def get_job_output(
        self, job_number: int, step: int, parallel_index: int | None
    ) -> JobOutput:
        """Get job output."""
        if parallel_index is None:
            job_details = await self.get_job_details(job_number)
            if job_details.details.parallelism > 1:
                raise AppError("parallel index is required for parallel jobs")
            else:
                parallel_index = 0

        job_output = self.cache_manager.get_job_output(job_number, step, parallel_index)
        if job_output is None:
            # !Note: We can't cache the V1 job details call here since the presigned URL expires
            job_details = await self.api_client.get_v1_job_details(
                self.project_slug, job_number
            )
            try:
                step_obj = job_details.steps[step]
            except IndexError:
                raise AppError(f"No steps matching filter (step={step})")
            actions = [a for a in step_obj.actions if a.index == parallel_index]
            if len(actions) == 0:
                raise AppError(
                    f"No steps matching filter (parallel_index={parallel_index})"
                )
            assert len(actions) == 1, f"found {len(actions)} matching actions"
            action = actions[0]
            output_url = action.output_url
            if output_url is None:
                raise AppError("Output URL not found")
            job_output = await self.api_client.get_job_output(output_url)
            self.cache_manager.set_job_output(
                job_number, job_details.lifecycle, step, parallel_index, job_output
            )
        return job_output

    async def get_job_tests(
        self,
        job_number: int,
        statuses: Container[api_types.JobTestResult] | None = None,
        file_suffix: str | None = None,
    ) -> list[JobTestMetadata]:
        """Get test metadata for a job, with optional filtering."""
        tests = self.cache_manager.get_job_tests(job_number)
        if tests is None:
            job_details = await self._get_job_details(job_number)
            tests = await self.api_client.get_job_tests(self.project_slug, job_number)
            self.cache_manager.set_job_tests(job_number, job_details.status, tests)

        if statuses is not None:
            tests = [t for t in tests if t.result in statuses]

        if file_suffix is not None:
            tests = [
                t for t in tests if t.file is not None and t.file.endswith(file_suffix)
            ]

        return tests

    async def get_workflow_failed_tests(self, workflow_id: str) -> WorkflowFailedTests:
        workflows_with_jobs = await self.get_workflow_jobs(
            None, [workflow_id], statuses={api_types.JobStatus.failed}
        )
        workflow_with_jobs = workflows_with_jobs[0]

        # Fetch tests for all failed jobs concurrently
        failed_jobs = [j for j in workflow_with_jobs.jobs if j.job_number is not None]
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self.get_job_tests(j.job_number))  # type: ignore[arg-type]
                for j in failed_jobs
            ]
        tests_lists = [task.result() for task in tasks]

        # Group failed tests across jobs
        failed_tests: dict[FailedTest, list[FailedTestJobInfo]] = defaultdict(list)
        for job, tests in zip(failed_jobs, tests_lists, strict=True):
            for test in tests:
                if test.result != api_types.JobTestResult.failure:
                    continue
                key = FailedTest(
                    file=test.file, classname=test.classname, name=test.name
                )
                failed_tests[key].append(
                    FailedTestJobInfo(
                        job_number=job.job_number,
                        job_name=job.name,
                    )
                )

        return WorkflowFailedTests(
            workflow=workflow_with_jobs.workflow,
            failed_tests=dict(failed_tests),
        )

    @staticmethod
    def _get_branch(branch: str) -> str:
        if branch == CURRENT_BRANCH:
            current_branch = git.get_current_branch()
            if current_branch is None:
                raise AppError("Current branch could not be determined")
            branch = current_branch
        return branch

    async def _get_latest_pipeline_for_current_branch(self) -> api_types.Pipeline:
        branch = self._get_branch(CURRENT_BRANCH)
        pipeline = await self.get_latest_pipeline(branch)
        if not pipeline:
            raise AppError(f"No pipelines found (branch '{branch}')")
        return pipeline

    async def _get_workflow(self, workflow_id: str) -> api_types.Workflow:
        workflow = self.cache_manager.get_workflow(workflow_id)
        if workflow is None:
            workflow = await self.api_client.get_workflow(workflow_id)
            self.cache_manager.set_workflow(workflow)
        return workflow

    async def _get_workflow_jobs(
        self, workflow: api_types.Workflow
    ) -> list[api_types.Job]:
        jobs = self.cache_manager.get_workflow_jobs(workflow.id)
        if jobs is None:
            jobs = await self.api_client.get_workflow_jobs(workflow.id)
            self.cache_manager.set_workflow_jobs(workflow.id, workflow.status, jobs)
        return jobs

    async def _get_job_details(self, job_number: int) -> api_types.JobDetails:
        job_details = self.cache_manager.get_job_details(job_number)
        if job_details is None:
            job_details = await self.api_client.get_job_details(
                self.project_slug, job_number
            )
            self.cache_manager.set_job_details(job_number, job_details)
        return job_details

    async def _get_v1_job_details(self, job_number: int) -> api_types.V1JobDetails:
        v1_job_details = self.cache_manager.get_v1_job_details(job_number)
        if v1_job_details is None:
            v1_job_details = await self.api_client.get_v1_job_details(
                self.project_slug, job_number
            )
            self.cache_manager.set_v1_job_details(job_number, v1_job_details)
        return v1_job_details


def _count_jobs_by_status(
    jobs: list[api_types.Job],
) -> dict[api_types.JobStatus, int]:
    return dict(Counter(job.status for job in jobs))


class _BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)


class PipelineWithWorkflows(_BaseModel):
    pipeline: api_types.Pipeline
    workflows: list[api_types.Workflow]


class WorkflowWithJobs(_BaseModel):
    workflow: api_types.Workflow
    jobs: list[api_types.Job]
    job_counts_by_status: dict[api_types.JobStatus, int]


class JobDetailsWithSteps(_BaseModel):
    details: api_types.JobDetails
    steps_by_action_index: dict[int, list[StepAction]]


class StepAction(_BaseModel):
    step_index: int
    step: api_types.V1JobStep
    action: api_types.V1JobAction


class WorkflowFailedTests(_BaseModel):
    workflow: api_types.Workflow
    failed_tests: dict[FailedTest, list[FailedTestJobInfo]]


class FailedTest(_BaseModel):
    file: str | None
    classname: str
    name: str


class FailedTestJobInfo(_BaseModel):
    job_number: int | None
    job_name: str


JobOutput = api_types.JobOutput
JobTestMetadata = api_types.JobTestMetadata
