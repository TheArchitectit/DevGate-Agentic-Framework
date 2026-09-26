#!/usr/bin/env python3
"""Mutation battery for the Zig comment-line slice (F1, 2026-09-26).

Each mutation is a single edit to shipped code that makes a specific promise
false while leaving everything else alone. A mutation is KILLED when one of the
named test files fails because of it; a SURVIVOR means a guard no test actually
depends on — the guard is decoration, and the suite would not notice its removal.

The promise under test: Zig comment lines are comments. `.zig` entered
SOURCE_EXTENSIONS (8c7556d) without entering isCommentLine's two hard-coded
extension lists, so the skip-comment-only-lines contract never applied to Zig
and a `///` doc comment mentioning @panic or std.debug.print fired PREVENT-Z-004
/ 005 as if it were code. The fix added `.zig` to both lists; the battery pins
each list independently, because a future edit that removes one of the two
tokens must not read as green.

Sibling of tests/mutation_battery_size_scope.py; same contract, same output.
"""
import sys

import mutation_harness  # noqa: E402  (sibling module, tests/ is sys.path[0])


SCAN = "scripts/guardrails-scan.mjs"
# The named fixture is the PYTEST bridge over the node suite, not the .mjs
# itself: the battery runs pytest, pytest collects nothing from a .mjs file,
# and the resulting exit-5 would read as a kill — 3/3 "killed" against a
# suite that never ran. tests/test_guardrails_scan_node.py runs the real
# suite and asserts the zig-comment section executed.
T_SCAN = "tests/test_guardrails_scan_node.py"

# Anchor and mutant for the FULL-LINE list. The with/without pair differs by
# exactly the `.zig` token, which is what makes the mutation real rather than
# a resyntax.
FULL_WITH_ZIG = ('[".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".svelte", '
                 '".rs", ".go", ".java", ".kt", ".gd", ".php", ".zig"].includes(ext)')
FULL_WITHOUT_ZIG = ('[".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".svelte", '
                    '".rs", ".go", ".java", ".kt", ".gd", ".php"].includes(ext)')

# The trailing-comment list does not exist: the second includes(ext) block in
# isCommentLine computed commentIdx/beforeComment and discarded both — a dead
# branch, removed with this slice (trailing comments on code lines are scanned
# by documented design, for every // language). ZC2/ZC3 therefore target what
# actually governs Zig behavior now: the list itself, and its interaction with
# the test-file rule (a comment line inside a *_test.zig file is doubly out of
# scope for blocking rules).
MUTATIONS = [
    # ZC1 — the full-line list. Killed by the doc-comment arm of section 16:
    # a `///` doc comment mentioning @panic/std.debug.print must be silent.
    ("ZC1: `.zig` dropped from the full-line comment list — doc comments fire again",
     [(SCAN, FULL_WITH_ZIG, FULL_WITHOUT_ZIG)],
     [T_SCAN], {}),

    # ZC2 — the whole isCommentLine call collapsed for Zig: a mutant that makes
    # ext lookup return a language with no comment grammar (`zz`), so every Zig
    # line, comment or code, is scanned as code. Kills prove the doc-comment
    # arm of section 16 is the guard, not an accident of the walk.
    ("ZC2: isCommentLine ext mapped to a grammarless language — Zig comments scanned as code",
     [(SCAN, "const ext = \".\" + file.split(\".\").pop();",
            "const ext = \".zz\";")],
     [T_SCAN], {}),

    # ZC3 — the comment-skip gate itself inverted: comment lines are scanned,
    # code lines skipped. If section 16's doc-comment arm can survive this,
    # the guard was not the guard.
    ("ZC3: comment-skip decision inverted — comments scanned, code skipped",
     [(SCAN, "if (!rule.scan_comments && isCommentLine(scanLine, ext)) continue;",
            "if (!rule.scan_comments && !isCommentLine(scanLine, ext)) continue;")],
     [T_SCAN], {}),
]

# Must SURVIVE. See the docstring: this pins the harness's own kill detection,
# not a fixture property.
NEGATIVE_CONTROLS = [
    ("N1: a language nobody wrote — must change no outcome",
     [(SCAN, FULL_WITH_ZIG,
       FULL_WITH_ZIG.replace('".php", ".zig"]', '".php", ".nim", ".zig"]'))],
     [T_SCAN], {}),
]


if __name__ == "__main__":
    sys.exit(mutation_harness.main(
        MUTATIONS, NEGATIVE_CONTROLS,
        "this one MUST survive — it pins the battery's own kill detection"))
