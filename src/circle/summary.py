from rich.text import Text


def try_extract_summary(message: str) -> str | None:
    """
    Try to extract summary from output. Returns None if extraction fails.

    Only supports pytest output, for now.
    """
    lines = message.split("\n")

    # Find the "short test summary info" section
    summary_start = None
    for i, line in enumerate(lines):
        plain_line = Text.from_ansi(line).plain
        if (
            plain_line.startswith("=")
            and "short test summary info" in plain_line.lower()
        ):
            summary_start = i
            break

    if summary_start is None:
        return None

    # Find the final summary line (contains "passed", "failed", etc. with timing)
    summary_end = None
    for i in range(summary_start + 1, len(lines)):
        line = lines[i]
        plain_line = Text.from_ansi(line).plain
        # Look for the final summary line with timing info
        if (
            plain_line.startswith("=")
            and ("passed" in plain_line.lower() or "failed" in plain_line.lower())
            and "in " in plain_line.lower()
        ):
            summary_end = i
            break

    if summary_end is None:
        return None

    # Extract the summary section
    summary_lines = lines[summary_start : summary_end + 1]
    return "\n".join(summary_lines)
