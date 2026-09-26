#!/usr/bin/env python3
"""Mutation battery for the wire-contract deprecation slice (S8:1020, 2026-09-26).

The promise under test: a retired `api_version` fails exit 40 with a reason
that names its retirement — and a foreign version does NOT get that reason —
while the current version is never judged by anything but itself. Each
mutation below makes one of those promises false in a way that would
otherwise read as green.
"""
import sys

import mutation_harness  # noqa: E402  (sibling module, tests/ is sys.path[0])


MAIN = "hub/coherence/__main__.py"
COMPAT = "hub/coherence/compat.py"
T = "tests/test_hub_coherence_compat.py"

# The gate's dispatch, as shipped: classify() decides the reason. The with/
# without pairs differ by exactly the clause that matters.
GATE_SHIPPED = ("        if status != \"current\":\n"
                "            reason = (compat.retired_note(req.get(\"api_version\"))\n"
                "                      if status == \"retired\"\n"
                "                      else f\"unsupported api_version {req.get('api_version')!r}; \"\n"
                "                           f\"supported: {SUPPORTED_API}\")")
GATE_NO_RETIRE = ("        if status != \"current\":\n"
                  "            reason = (f\"unsupported api_version {req.get('api_version')!r}; \"\n"
                  "                           f\"supported: {SUPPORTED_API}\")")

RETIRE_GUARD_SHIPPED = '    if version == current():\n        raise ValueError(\n            f"refusing to retire {version!r}: it is the currently emitted "\n            f"version; ship the successor first")\n'
RETIRE_GUARD_GONE = ""

MUTATIONS = [
    # RC1 — the gate collapses retired back into the generic refusal. The
    # slice's core distinction disappears; the distinguishability test kills
    # it on "retired on 2026-09-01".
    ("RC1: gate drops the retired-reason branch — retired reads as generic unsupported",
     [(MAIN, GATE_SHIPPED, GATE_NO_RETIRE)],
     [T], {}),

    # RC2 — the current-version guard in retire() removed: the live contract
    # can be turned off through the registry.
    ("RC2: retire() loses the refuse-current guard — the emitted version can be retired",
     [(COMPAT, RETIRE_GUARD_SHIPPED, RETIRE_GUARD_GONE)],
     [T], {}),
]

# Must SURVIVE: the control pins the battery's own kill detection, not a
# fixture property. isoformat() and str() are identical on a date, so this
# mutation provably changes no behavior; a kill would mean a test asserts
# source shape rather than outcome. (The naive control — dangling extra
# registry entries — is WRONG here: the table-vs-registry equality test
# legitimately kills any registry change, so it is not "changes no outcome".)
NEGATIVE_CONTROLS = [
    ("N1: isoformat() -> str() on a date — byte-identical output, must change no outcome",
     [(COMPAT, 'f"api_version {api_version!r} was retired on {retired_on.isoformat()}"',
       'f"api_version {api_version!r} was retired on {str(retired_on)}"')],
     [T], {}),
]


if __name__ == "__main__":
    sys.exit(mutation_harness.main(
        MUTATIONS, NEGATIVE_CONTROLS,
        "this one MUST survive — it pins the battery's own kill detection"))
