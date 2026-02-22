---
name: circle-cli
description: Views CircleCI pipelines, workflows, jobs, and output. Use when investigating CI failures or checking pipeline status.
---

# CircleCI CLI

**Always use `-o markdown` (`--output-format markdown`) for agent-readable output with explicit URLs, precise timestamps and durations.**

## Commands

```bash
circle pipelines list -o markdown                                    # Recent pipelines for current branch
circle pipelines list -o markdown --branch main -n 5                 # 5 pipelines for main branch

circle pipelines details -o markdown <id-or-number>                  # Pipeline detail

circle workflows list -o markdown --pipeline <id-or-number>                    # Workflows for a pipeline

circle jobs list -o markdown --pipeline <id-or-number>                         # All jobs for a pipeline
circle jobs list -o markdown --pipeline <id-or-number> --status failed         # Only failed jobs
circle jobs list -o markdown --pipeline <id-or-number> --status not:success    # All non-successful jobs

circle jobs details -o markdown <job-number>                         # Job steps
circle jobs details -o markdown <job-number> --step-status failed    # Only failed steps

circle jobs tests -o markdown <job-number> --status failed           # Failed tests (use BEFORE output!)
circle jobs tests -o markdown <job-number> --status failed -m        # Failed tests with messages
circle jobs tests -o markdown <job-number> --status not:success      # All non-successful tests

circle jobs output -o markdown <job-number> --step <n>               # Step output (expensive, use last)
circle jobs output -o markdown <job-number> --step <n> --try-extract-summary   # Extract test summary
circle jobs output -o markdown <job-number> --step <n> --parallel-index <i>    # Parallel run output

circle failed-tests -o markdown                                               # Failed tests for latest pipeline
circle failed-tests -o markdown --pipeline <id-or-number>                      # Failed tests for a pipeline
circle failed-tests -o markdown --workflow <workflow-id>                        # Failed tests for specific workflow(s)
circle failed-tests -o markdown --unique file                                  # Unique failing files
circle failed-tests -o markdown --unique classname                             # Unique failing classnames
circle failed-tests -o markdown --include-jobs                                 # Include which jobs each test failed in
```

## Investigating failures

**IMPORTANT: Conserve tokens by using targeted commands. Filter for failures.**

1. `circle pipelines list` or `circle pipelines details <id-or-number>` - find the failing pipeline
2. `circle jobs list --pipeline <id-or-number> --status not:success` - find failed jobs
3. `circle failed-tests` or `circle failed-tests --pipeline <id-or-number>` - overview of all failed tests across workflows (but remember other jobs e.g. linting might also have failed)
4. `circle jobs details <job-number> --step-status not:success` - find failed steps
5. `circle jobs tests <job-number> --status not:success` - identify which tests failed in a specific job
6. `circle jobs tests <job-number> --status not:success -m` - view failure messages (often sufficient to diagnose)
7. `circle jobs output <job-number> --step <n> --try-extract-summary` - only if more context needed (higher token cost)
8. `circle jobs output <job-number> --step <n>` - last resort

**Key principle:** Use `jobs tests --status failed` before `jobs output`. Test metadata is compact; full output is expensive. The failure messages (`-m`) often contain enough information to diagnose the issue.

Investigate all failures unless told otherwise. Watch for flaky or unrelated failures.

## URLs

If given a CircleCI URL, extract the pipeline ID/number, workflow ID, or job number from it and use the appropriate command.
