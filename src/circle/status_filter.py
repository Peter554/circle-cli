from __future__ import annotations

import dataclasses
import enum
from collections.abc import Container

import pydantic


@dataclasses.dataclass(frozen=True)
class StatusFilter[T](Container[T]):
    """Filter that supports both inclusion and exclusion of statuses.

    Supports the ``in`` operator so it can be used as a drop-in replacement
    for a set in filtering code like ``if status in filter``.
    """

    include: frozenset[T]
    exclude: frozenset[T]

    def __contains__(self, item: object) -> bool:
        if self.include and item not in self.include:
            return False
        if self.exclude and item in self.exclude:
            return False
        return True


def parse_enum_statuses[T: enum.StrEnum](
    raw_values: list[str],
    status_type: type[T],
    aliases: dict[str, str] | None = None,
) -> StatusFilter[T]:
    """Parse raw status strings into a StatusFilter.

    Supports:
    - ``"success"`` -> include success
    - ``"not:success"`` -> exclude success
    - Aliases: ``"failed"`` -> ``"failure"`` (for test results)
    """
    adapter = pydantic.TypeAdapter(status_type)
    includes: set[T] = set()
    excludes: set[T] = set()

    for raw in raw_values:
        if raw.startswith("not:"):
            raw = raw[4:]
            raw = (aliases or {}).get(raw, raw)
            parsed = adapter.validate_python(raw)
            excludes.add(parsed)
        else:
            raw = (aliases or {}).get(raw, raw)
            parsed = adapter.validate_python(raw)
            includes.add(parsed)

    return StatusFilter(include=frozenset(includes), exclude=frozenset(excludes))


def parse_str_statuses(
    raw_values: list[str],
    aliases: dict[str, str] | None = None,
) -> StatusFilter[str]:
    """Parse raw status strings (no enum validation) into a StatusFilter."""
    includes: set[str] = set()
    excludes: set[str] = set()

    for raw in raw_values:
        if raw.startswith("not:"):
            raw = raw[4:]
            raw = (aliases or {}).get(raw, raw)
            excludes.add(raw)
        else:
            raw = (aliases or {}).get(raw, raw)
            includes.add(raw)

    return StatusFilter(include=frozenset(includes), exclude=frozenset(excludes))
