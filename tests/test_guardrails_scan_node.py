#!/usr/bin/env python3
"""Pytest bridge over the node scanner suite (tests/test_guardrails_scan.mjs).

The mutation batteries run through pytest (tests/mutation_harness.py), so a
guard asserted only in a node suite is unreachable from a battery: pytest
collects nothing from a .mjs file, the empty collection exits 5, and the
harness reads any non-zero exit as a KILL — 3/3 killed against a suite that
never ran. This bridge makes the node suite pytest-addressable so
tests/mutation_battery_zig_comment.py can name it.

It runs the real suite (spawn, not re-implement) and asserts three things the
battery's mutants must be able to break: the suite passed, the Zig comment
section's checks ran, and the Zig section reported no failure. Sections that
the suite silently loses (the truncation bug 7e73044 fixed in cleanup()) would
fail the ran-check — a truncated run is not a pass.
"""
import os
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class TestGuardrailsScanNodeSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proc = subprocess.run(
            ["node", "tests/test_guardrails_scan.mjs"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO), env=dict(os.environ))

    def test_node_suite_passes(self):
        self.assertEqual(self.proc.returncode, 0,
                         f"node suite failed:\n{self.proc.stderr[-2000:]}")

    def test_the_zig_comment_section_actually_ran(self):
        # Anti-truncation: the checks assert `ok -` lines; if cleanup() ever
        # re-learns to throw and the suite aborts before section 16, the pass
        # count drops and this fails even though returncode would read fine.
        self.assertGreaterEqual(
            self.proc.stdout.count("ok - zig comment"), 2,
            f"zig comment section did not run:\n{self.proc.stdout[-2000:]}")

    def test_the_suite_reports_no_failures_in_its_own_words(self):
        self.assertNotIn("FAIL -", self.proc.stdout,
                         "the suite printed its own FAIL line")
        self.assertNotIn("TEST(S) FAILED", self.proc.stdout)


if __name__ == "__main__":
    unittest.main()
