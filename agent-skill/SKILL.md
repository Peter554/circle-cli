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
circle pipelines

# View workflows for latest pipeline
circle workflows

# View jobs (filter by status)
circle jobs --status failed

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

1. Check recent pipelines: `circle pipelines`
2. View workflows for the failing pipeline: `circle workflows --pipeline <id>`
3. Find failed jobs: `circle jobs --status failed`
4. View failed steps: `circle job details <job-number> --step-status failed`
5. View output: `circle job output <job-number> --step <step-number>`.
  * Try first to extract summary via `--try-extract-summary` flag, it saves tokens.
    If that output is unclear then run again without the flag to get the full output.
  * For parallel runs, specify the parallel index via the `--parallel-index flag.
