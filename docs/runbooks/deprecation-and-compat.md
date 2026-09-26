# Deprecation & compatibility policy — the wire contract

Scope: the coherence service's wire `api_version`
(`devgate.spec-coherence/vN`, `hub/coherence/__main__.py` `SUPPORTED_API`)
and the schema family it governs
(`openspec/changes/devgate-spec-coherence-service/schemas/`).

## The compatibility rule

A build judges a request only under the contract version it was built with
(coh-dec-04). A request whose `api_version` differs in any way is refused
with `error.class: "protocol"`, exit 40, **before any resolver runs** —
the refusal is the contract. There is no best-effort parsing of a foreign
version and no defaulting a missing version to v1.

## Supported versions

| Version | Status | Emitted by | Refusal text |
|---|---|---|---|
| `devgate.spec-coherence/v1` | current (only) | every build to date | — |

A version leaves this table in exactly one direction: current → retired.
A version never exists in two states at once, and there is no "deprecated
but accepted" state — the day a version stops being judged is the day it
is retired.

## The three refusal kinds (exit 40 in all cases, different reasons)

| Request's `api_version` | Meaning | What the envelope says |
|---|---|---|
| current | accepted | — |
| retired | a real predecessor, past its window | `compat.retired_note`: names the version, was **retired on** its recorded date, and the upgrade direction |
| foreign | never existed, mistyped family, or newer than this build | the generic `unsupported api_version …; supported: …` line |

The distinction is deliberate: an operator with a stale hub must be able to
tell "my emitter is behind, upgrade it" from "my emitter is mistyped or
corrupt" without reading source. `hub/coherence/compat.py:classify` makes
the distinction; the registry (`_RETIRED`) is code, reviewed like the gate.

## Deprecation procedure (when v2 is shipped)

1. **Announce** — add the successor to this policy doc's supported-versions
   table as `current`; record the predecessor's announcement date here.
2. **Window** — the predecessor remains `current`-judged while builds roll
   out. This repository ships one binary gate per build; the window lives in
   the fleet rollout, not in the gate.
3. **Retire** — in the release that stops judging the predecessor:
   call `compat.retire("<old>", retired_on=<date>, note="<reason>")` in
   `hub/coherence/compat.py`'s `_RETIRED`, update the table above, and ship
   the new `SUPPORTED_API` in the same change. `retire()` refuses to retire
   the currently emitted version — retirement follows shipping the successor,
   never replaces it.
4. **Evidence** — the retired version keeps its own refusal reason forever;
   a hub pinned to it fails closed with a self-explaining envelope, and the
   runbook below triages it.

There is no re-activation path: retiring is a judgment that the version can
no longer be trusted to be judged at all (the anti-rollback posture of
coh-pol-01 applies to the contract itself).

## Runbook triage — retired vs foreign exit 40

```bash
# The request the stale side wrote:
jq -r .api_version /path/to/request.json
```

- `devgate.spec-coherence/v2` (or other retired) → the emitting side is a
  real predecessor past its deprecation window. The envelope already says
  "upgrade the emitting side"; do not edit the schema to accept it.
- anything else → mistyped, corrupt, or a *newer* version than this build.
  If newer: this build is behind — upgrade it. Either way the fix is a
  version alignment, not a schema edit.

## Pinned by

`tests/test_hub_coherence_compat.py` (supported-versions table as an
asserted fixture; classify/retire behavior; the current-never-retired
guard) and `tests/test_hub_coherence_exitcodes.py` (exit 40 reachable,
`error.class: "protocol"`); the runbook-claims gate
(`tests/test_runbook_claims.py`) pins this file's anchors by name.
