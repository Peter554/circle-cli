"""Rich output formatting for CLI."""

from typing import NoReturn

from rich.console import Console

console = Console()


def print(o: object) -> None:
    console.print(o)


def error(message: str) -> NoReturn:
    console.print(f"[red]Error:[/red] {message}", highlight=False)
    raise SystemExit(1)
