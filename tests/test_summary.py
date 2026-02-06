from circle.summary import try_extract_summary


class TestTryExtractSummary:
    def test_extracts_summary_from_pytest_output(self):
        output = """\
tests/test_foo.py::test_one PASSED
tests/test_foo.py::test_two FAILED
tests/test_foo.py::test_three PASSED

=========================== short test summary info ============================
FAILED tests/test_foo.py::test_two - AssertionError: assert 1 == 2
========================= 1 failed, 2 passed in 0.05s =========================
"""

        expected_summary = """\
=========================== short test summary info ============================
FAILED tests/test_foo.py::test_two - AssertionError: assert 1 == 2
========================= 1 failed, 2 passed in 0.05s ========================="""

        assert try_extract_summary(output) == expected_summary

    def test_extracts_multiline_summary(self):
        output = """\
tests/test_a.py::test_x FAILED
tests/test_b.py::test_y FAILED
tests/test_b.py::test_z PASSED

=========================== short test summary info ============================
FAILED tests/test_a.py::test_x - assert False
FAILED tests/test_b.py::test_y - ValueError
========================= 2 failed, 1 passed in 0.10s =========================
"""

        expected_summary = """\
=========================== short test summary info ============================
FAILED tests/test_a.py::test_x - assert False
FAILED tests/test_b.py::test_y - ValueError
========================= 2 failed, 1 passed in 0.10s ========================="""

        assert try_extract_summary(output) == expected_summary

    def test_extracts_summary_with_ansi_codes(self):
        """ANSI escape codes in the = delimiter lines don't prevent matching."""
        output = """\
tests/test_foo.py::test_one FAILED

\x1b[1m=========================== short test summary info ============================\x1b[0m
\x1b[31mFAILED tests/test_foo.py::test_one - assert False\x1b[0m
\x1b[31m========================= 1 failed in 0.03s =========================\x1b[0m
"""

        expected_summary = """\
\x1b[1m=========================== short test summary info ============================\x1b[0m
\x1b[31mFAILED tests/test_foo.py::test_one - assert False\x1b[0m
\x1b[31m========================= 1 failed in 0.03s =========================\x1b[0m"""

        assert try_extract_summary(output) == expected_summary
