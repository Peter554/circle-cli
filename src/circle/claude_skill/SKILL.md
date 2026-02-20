---
name: circle-cli
description: Views CircleCI pipelines, workflows, jobs, and output. Use when investigating CI failures or checking pipeline status.
---

# CircleCI CLI

## Commands

```bash
circle pipelines list                                    # Recent pipelines for current branch
circle pipelines list --branch main -n 5                 # 5 pipelines for main branch

circle pipelines details <id-or-number>                  # Pipeline detail

circle workflows list --pipeline <id-or-number>                    # Workflows for a pipeline

circle jobs list --pipeline <id-or-number>                         # All jobs for a pipeline
circle jobs list --pipeline <id-or-number> --status failed         # Only failed jobs

circle jobs details <job-number>                         # Job steps
circle jobs details <job-number> --step-status failed    # Only failed steps

circle jobs tests <job-number> --status failed           # Failed tests (use BEFORE output!)
circle jobs tests <job-number> --status failed -m        # Failed tests with messages

circle jobs output <job-number> --step <n>               # Step output (expensive, use last)
circle jobs output <job-number> --step <n> --try-extract-summary   # Extract test summary
circle jobs output <job-number> --step <n> --parallel-index <i>    # Parallel run output
```

## Investigating failures

**IMPORTANT: Conserve tokens by using targeted commands. Filter for failures.**

1. `circle pipelines list` or `circle pipelines details <id-or-number>` - find the failing pipeline
2. `circle jobs list --pipeline <id-or-number> --status failed` - find failed jobs
3. `circle jobs details <job-number> --step-status failed` - find failed steps
4. `circle jobs tests <job-number> --status failed` - identify which tests failed (low token cost)
5. `circle jobs tests <job-number> --status failed -m` - view failure messages (often sufficient to diagnose)
6. `circle jobs output <job-number> --step <n> --try-extract-summary` - only if more context needed (high token cost)
7. `circle jobs output <job-number> --step <n>` - last resort


**Key principle:** Use `jobs tests --status failed` before `jobs output`. Test metadata is compact; full output is expensive. The failure messages (`-m`) often contain enough information to diagnose the issue.

Investigate all failures unless told otherwise. Watch for flaky or unrelated failures.

## URLs

If given a CircleCI URL, extract the pipeline ID/number, workflow ID, or job number from it and use the appropriate command.
