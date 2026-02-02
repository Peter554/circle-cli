---
name: circle-cli
description: Views CircleCI pipelines, workflows, jobs, and output. Use when investigating CI failures, debugging test failures, checking pipeline status, or viewing job logs without opening a browser.
---

# CircleCI CLI

A CLI for quickly viewing CircleCI pipeline status, job details, and output.

## Quick reference

```bash
# View help
circle --help

# View recent pipelines
circle pipelines list

# View workflows
circle workflows list --pipeline <pipeline-id>

# View jobs (filter by status)
circle jobs list --pipeline <pipeline-id> --status failed

# View job details and steps
circle job details <job-number>

# Filter job steps by status
circle job details <job-number> --step-status failed

# View job output
circle job output <job-number> --step <step-number>

# Extract pytest summary
circle job output <job-number> --step <step-number> --try-extract-summary
```

## Investigating a failed pipeline

When a user reports a CI failure or you need to debug failing tests:

1. Check recent pipelines: `circle pipelines list`
2. View workflows for the failing pipeline: `circle workflows list --pipeline <pipeline-id>`
3. Find failed jobs: `circle jobs list --pipeline <pipeline-id> --status failed`
4. View failed steps: `circle job details <job-number> --step-status failed`
5. View output: `circle job output <job-number> --step <step-number>`.
  * Try first to extract summary via `--try-extract-summary` flag, it saves tokens.
    If that output is unclear or more details are required then run again without 
    that flag to get the full output.
  * For parallel runs, specify the parallel index via the `--parallel-index` flag.
6. Unless the user specifies otherwise, investigate all failures.
7. Be wary of flaky tests or unrelated failures. Try to work out which failures are 
   likely to be most relevant.
