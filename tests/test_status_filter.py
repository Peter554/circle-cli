import pytest

from circle import api_types
from circle.status_filter import (
    StatusFilter,
    parse_enum_statuses,
    parse_str_statuses,
)


class TestStatusFilter:
    def test_include_only(self):
        f = StatusFilter(include=frozenset({"a", "b"}), exclude=frozenset())
        assert "a" in f
        assert "b" in f
        assert "c" not in f

    def test_exclude_only(self):
        f = StatusFilter(include=frozenset(), exclude=frozenset({"a"}))
        assert "a" not in f
        assert "b" in f
        assert "c" in f

    def test_include_and_exclude(self):
        f = StatusFilter(include=frozenset({"a", "b"}), exclude=frozenset({"b"}))
        assert "a" in f
        assert "b" not in f
        assert "c" not in f

    def test_exclude_takes_precedence_over_include(self):
        f = StatusFilter(include=frozenset({"a"}), exclude=frozenset({"a"}))
        assert "a" not in f

    def test_empty_matches_everything(self):
        f: StatusFilter[str] = StatusFilter(include=frozenset(), exclude=frozenset())
        assert "a" in f
        assert "anything" in f


class TestParseEnumStatuses:
    def test_single_include(self):
        result = parse_enum_statuses(["success"], api_types.JobStatus)
        assert api_types.JobStatus.success in result
        assert api_types.JobStatus.failed not in result

    def test_multiple_includes(self):
        result = parse_enum_statuses(["success", "failed"], api_types.JobStatus)
        assert api_types.JobStatus.success in result
        assert api_types.JobStatus.failed in result
        assert api_types.JobStatus.running not in result

    def test_single_exclude(self):
        result = parse_enum_statuses(["not:success"], api_types.JobStatus)
        assert api_types.JobStatus.success not in result
        assert api_types.JobStatus.failed in result
        assert api_types.JobStatus.running in result

    def test_multiple_excludes(self):
        result = parse_enum_statuses(
            ["not:success", "not:running"], api_types.JobStatus
        )
        assert api_types.JobStatus.success not in result
        assert api_types.JobStatus.running not in result
        assert api_types.JobStatus.failed in result

    def test_mixed_include_and_exclude(self):
        result = parse_enum_statuses(
            ["failed", "running", "not:running"], api_types.JobStatus
        )
        assert api_types.JobStatus.failed in result
        assert api_types.JobStatus.running not in result
        assert api_types.JobStatus.success not in result

    def test_alias(self):
        result = parse_enum_statuses(
            ["failed"], api_types.JobTestResult, aliases={"failed": "failure"}
        )
        assert api_types.JobTestResult.failure in result

    def test_alias_with_exclusion(self):
        result = parse_enum_statuses(
            ["not:failed"], api_types.JobTestResult, aliases={"failed": "failure"}
        )
        assert api_types.JobTestResult.failure not in result
        assert api_types.JobTestResult.success in result
        assert api_types.JobTestResult.skipped in result

    def test_invalid_status_raises(self):
        with pytest.raises(Exception):
            parse_enum_statuses(["nonexistent"], api_types.JobStatus)

    def test_invalid_excluded_status_raises(self):
        with pytest.raises(Exception):
            parse_enum_statuses(["not:nonexistent"], api_types.JobStatus)


class TestParseStrStatuses:
    def test_include(self):
        result = parse_str_statuses(["success", "failed"])
        assert "success" in result
        assert "failed" in result
        assert "other" not in result

    def test_exclude(self):
        result = parse_str_statuses(["not:success"])
        assert "success" not in result
        assert "failed" in result

    def test_mixed(self):
        result = parse_str_statuses(["failed", "not:success"])
        assert "failed" in result
        assert "success" not in result
        assert "running" not in result
