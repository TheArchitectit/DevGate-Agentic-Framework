# Stage 3 readiness review — evidence matrix (2026-09-26)

Purpose: the inputs for the Stage 3 readiness review (tasks.md:1109) that
gates any enforced fleet rollout. The 12 release acceptance criteria
(`acceptance.md`) are dispositioned one by one: **MET** (cited evidence),
**OPEN** (named blocker), or **BLOCKED** (owner decision outstanding).
This document is factual: a criterion is MET only when the evidence is a
shipped test, drill, or measured run — not prose intent.

## The 12 release acceptance criteria

| # | Criterion (paraphrase) | Disposition | Evidence |
|---|---|---|---|
| 1 | All normative schemas versioned + compat tests | **MET** | 15 schemas carry `<family>/vN` (`FAMILY_RE`, `schemacheck.py`); compat machinery shipped 53384ac (`compat.py` retirement registry, branching refusal, policy runbook, 2-mutant battery; hosted green on run 36273664935) |
| 2 | Canonical replay 100 consecutive runs per architecture | **MET (shipped surface)** | `determinism_drill.py --runs 100` PASS 100/100 byte-identical, 2026-09-26 (sha 3d0b8ccbd9ccefd2…); one profile (`linux-amd64-v1`) shipped, so per-architecture coverage is complete for the shipped surface; arm64 stays open until a second profile exists |
| 3 | Every required assertion exactly once in result accounting | **MET** | C2 multi-finding ledger (9e58fbf + round-13 audit): per-assertion findings, strictest-class mirror, order-invariance both-orders agreement test; no last-wins collapse |
| 4 | Required skips/errors block in enforced mode | **MET** | Adapter default-deny (tasks.md:764 closure, coh-int-05): exit-code/decision agreement at the container boundary; exit 32 on timeout/overflow; coh-int-06 five skip paths all non-green |
| 5 | Local policy cannot weaken central policy | **MET** | `TestOverlayCannotWeaken` (A10); anti-rollback nc-09; grandfather windows |
| 6 | Container: non-root, read-only, caps, sockets, resources, redaction, default-deny egress | **MET** | Launcher 34-test suite + container suite; escape review (995afc1) enumerates all ten vectors with pinned controls; rootless podman measured on both hosts |
| 7 | Signed attestation detects bound-digest substitution | **MET** | `--verify-run` nine-step fail-closed chain; `test_bound_digest_tamper_is_detected` + `test_statement_digest_check_is_independently_load_bearing` mutate one bound at a time; nc-10 |
| 8 | Adoption ladder enforces advisory expiry + Stage 2 no-regression | **advisory-expiry MET; no-regression OPEN** | advisory escalation model ratified 8bf51d8, `adoption.evaluate` enforcement built; the **ratchet demo against a real repo's named-debt baseline (LobsterWars 13 findings) is not yet run** — that demo is the criterion's live proof, sequenced with the pilots (R9 owner approval outstanding) |
| 9 | CI, local, fleet adapters equivalent canonical results | **MET (identity, not yet fleet-measured)** | Byte-equivalence-by-identity: CI and local run the identical builder bytes (`hub.coherence.invoke` inside the pinned image); the fleet half (a hosted coherence run on an enrolled spoke against a real subject) has not yet been run against a real repo — pilots |
| 10 | Six fixtures produce expected decisions | **synthetic MET; real-repo half BLOCKED (R9)** | Fixtures A–F shipped with expected decisions (synthetic, per R9); gamerepo01/LobsterWars-derived fixtures require R9 provenance capture + owner approval — the fixture set is honest about this (acceptance.md:87) |
| 11 | Operator reproduces any finding from its evidence bundle without the original runner | **MET** | Sealed-bundle design: `--verify-run` offline chain + `store.artifacts()` (durability path, containment-pinned); evidence objects self-contained with bound digests |
| 12 | Runbooks: outage, rollback, policy recovery, key rotation, evaluator revocation | **4/5 MET; evaluator revocation OPEN (owner decision)** | Outage/rollback/policy-recovery/key-rotation covered by drill/test-verified runbooks (:1031 measurement); evaluator revocation is a build gap needing an owner decision (new control-plane revocation record vs scoping to pinned-image lifecycle) — recorded at :1031, not improvised |

## The ten owner-decision open questions (acceptance.md) — status

| # | Question | Status |
|---|---| readiness |
| 1 | Authoritative OpenSpec approval mechanism | OPEN |
| 2 | Which assertion classes form the enforced core for the first pilot | OPEN |
| OQ3 | Max advisory age | OPEN (owner's number) — enforcement machinery shipped, blocked only on the number |
| 4 | Exception/rollback approvers | OPEN |
| 5 | Which architectures must be byte-equivalent at launch | PARTIALLY ANSWERED by the single-profile registry (amd64 only) |
| 6 | Offline evaluation: launch requirement or hardening milestone | OPEN |
| 7 | Evidence retention periods | OPEN (retention_class fallback shipped) |
| 8 | Backward-compatible result fields | OPEN |
| 9 | gamerepo01 normative vs historical facts | OPEN (R9 owner approval) |
| 10 | Vision determinism in the first 3D slice | OPEN (S7) |

## Verdict

**Not ready for enforced fleet rollout.** The code-surface criteria (1–7,
11) are MET with named tests and measured runs. What blocks Stage 3:

1. **Owner decisions** — 10 open questions, of which OQ3 (advisory age),
   OQ2 (enforced core), and the evaluator-revocation scope decision
   directly gate enforcement posture.
2. **Real pilots** — the R9 provenance capture + owner approval for real
   repo facts (gamerepo01 lineage, LobsterWars 13 findings) gates criteria
   8 (ratchet demo), 9 (fleet-half measurement), and 10 (real-fixture
   half). Runner availability is no longer a blocker: all 14 ucs03 spokes
   are enrolled + heartbeating as of 2026-09-25/26.
3. **Evaluator revocation build gap** — either the control-plane
   revocation record (coh-pol-02 machinery) or the owner's scoping to
   pinned-image lifecycle; either way a decision, then build-or-runbook.

The review's honest headline: **the gate is built and measured; the
enforcement posture is waiting on humans, not code.**
