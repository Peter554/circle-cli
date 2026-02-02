---
name: circle-cli
description: Views CircleCI pipelines, workflows, jobs, and output. Use when investigating CI failures or checking pipeline status.
---

# CircleCI CLI

## Commands

```bash
circle pipelines list                                    # Recent pipelines for current branch
circle pipelines list --branch main -n 5                 # 5 pipelines for main branch

circle workflows list --pipeline <id>                    # Workflows for a pipeline

circle jobs list --pipeline <id>                         # All jobs for a pipeline
circle jobs list --pipeline <id> --status failed         # Only failed jobs

circle jobs details <job-number>                         # Job steps
circle jobs details <job-number> --step-status failed    # Only failed steps

circle jobs output <job-number> --step <n>               # Step output
circle jobs output <job-number> --step <n> --try-extract-summary   # Extract test summary
circle jobs output <job-number> --step <n> --parallel-index <i>    # Parallel run output
```

## Investigating failures

1. `circle pipelines list` - find the failing pipeline
2. `circle workflows list --pipeline <id>` - see workflow status
3. `circle jobs list --pipeline <id> --status failed` - find failed jobs
4. `circle jobs details <job-number> --step-status failed` - find failed steps
5. `circle jobs output <job-number> --step <n> --try-extract-summary` - view output (try summary first to save tokens, then full output if needed). For parallel runs, add `--parallel-index <i>`.

Investigate all failures unless told otherwise. Watch for flaky or unrelated failures.
