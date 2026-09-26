# Threat Model — Spec Coherence Service

Scope: `hub/coherence/` (the signed-evaluation service), the evaluator
container, and the consumer-repo boundary. This document is factual: every
row cites the test that defeats the adversary class, or says **UNCOVERED**.
Anything UNCOVERED must not be marketed as covered.

## Trust boundaries

| Boundary | Who controls it | Note |
|---|---|---|
| Control plane → evaluator | control plane (stand-in: `HUB_COHERENCE_*` env + issued contexts) | Real KMS/key management is ADR-018; the HMAC stand-in is explicitly a pilot scope |
| Evaluator container → host | host launcher (`hub/coherence/launcher.py`) | read-only, non-root, cap-drop ALL, network=none |
| Consumer repo → evaluator | repository content (specs, overlays, assertion files) | repository content establishes identity, never authority (coh-pol-02) |

## Assets

- Signing keys (stand-in env keys) and the control-plane signer set
- The policy bundle (epoch, required assertions, approved evaluators/signers)
- Sealed evidence + canonical decisions (the things consumers act on)
- The decision cache (a wrong hit replays a stale verdict)

## Adversary classes and controls

| # | Adversary / attack class | Control | Test that defeats it |
|---|---|---|---|
| A1 | Forged countersignature on an evaluation context | HMAC verify at context load; unsigned context refused wherever a CP key is configured | `tests/test_hub_coherence_issue.py` (context signature guards); **UNCOVERED** for a full forged-signature negative control against a live key — see note |
| A2 | Replayed evaluation context (stale time / reused decision) | `semantics: replay` is structurally labeled non-promotion-authorizing; `attest.required()` demands fresh-promotion for signing | `tests/test_hub_coherence_ladder.py` (replay demotion); decision-cache TTL via `cache.py` predicates |
| A3 | Older-but-signed policy bundle accepted without a grandfather window | Anti-rollback: bundle `bundle_epoch` vs binding `min_bundle_epoch`; binding rides the signed context | `scripts/negative_controls.py` nc-09 (rolled-back bundle → exit 31); unit pins in `tests/test_hub_coherence_conformance.py` |
| A4 | Payload substitution under a still-valid attestation | Offline verification chain: statement digest, bound digests, signature, signer set, revocation, evidence re-verify | `scripts/negative_controls.py` nc-10 (substituted decision → `decision-digest-mismatch`); `scripts/negative_controls.py` nc-05 (unapproved evaluator) + attestation signer-set guards in `tests/test_hub_coherence_conformance.py` |
| A5 | Policy-refusal ambiguity (caller mistakes ERROR for FAIL/PASS) | Frozen exit matrix; decision/exit agreement asserted at the container boundary | `tests/test_hub_coherence_exitcodes.py`; adapter default-deny: exit-code/decision agreement pinned in `tests/test_hub_coherence_conformance.py` (round-7 remediation set) |
| A6 | Evidence tamper after sealing | Digest-sealed evidence + manifest; verify recomputes every object; containment on attacker-influenced paths | `tests/test_hub_coherence.py` tamper tests; `tests/test_hub_coherence_fw.py` (consistent-escaping bundle rejected); mutation-checked 21/21 |
| A7 | Evaluator image substitution | Digest-pinned refs; launcher injects executed digest; profile registry match | `tests/test_hub_coherence_container.py`; CI `container-image` job (digest vs identity registry, notice-only while S4 publish is in flight) |
| A8 | Cache poisoning / stale-hit | Total cache key (subject+package+policy+context+image+plugins+facts+TTL+retention+signer); TTL from trusted `evaluation_time`; malformed entries miss | `tests/test_hub_coherence_cache.py` (component drift, as_of TTL); retention via caller predicates |
| A9 | Evaluator-code mutation that verification cannot see | Mutation testing of the evidence module | `scripts/mutation_check.py` — evidence.py 21/21 killed; CI `evaluator-integrity` job |
| A10 | Malicious repository overlay (weaken central policy) | Overlay may strengthen only: unknown evaluator, severity below floor, disabling required, capability grants — all rejected | `tests/test_hub_coherence_conformance.py::TestOverlayCannotWeaken` |
| A11 | Gaming the benchmark (hardcode to pass hidden checks) | Hidden verifiers receive the repo under test as argv[1]; shipped GAMING strategy must stay rejected | CI `evaluator-integrity`: "Gaming strategy rejected" step; `.benchmarks/` control phase |
| A12 | Compromised runner (spoke) | One-time enrollment tokens; per-runner revocable heartbeat tokens; salted hashes at rest | `tests/test_hub_enroll_heartbeat.py`; `scripts/fleet_drill.py` (forged token 401, post-revoke 401, restart persistence) |

**Note on A1:** the countersignature guard is covered at the load/verify
level by the issue tests; a dedicated forged-signature negative control in
the style of nc-10 (craft a context, tamper the signature byte, assert the
rejection reason) would close the last gap and is welcome.

## Container escape review (evaluator boundary emphasis, 2026-09-26)

The evaluator container is the service's most hostile input: it executes
subject content that an adversarial repo wrote. Escape surface, per vector,
with the control that stands against it:

| Escape vector | Control in place | Pinned by |
|---|---|---|
| Root execution / privilege escalation in-container | `--user=<non-root>` (root refused at validation), `--cap-drop=ALL` (cap-add forbidden), `--security-opt=no-new-privileges` | `test_root_user_rejected`, `test_cap_drop_missing_rejected`, `test_cap_add_forbidden`, `test_args_enforce_isolation` (launcher suite) |
| Host network reach from the container | `--network=none` (host network refused explicitly) | `test_host_network_rejected`, `test_non_none_network_rejected` |
| Host filesystem write via rootfs | `--read-only --read-only-tmpfs`; every writable target is a bounded tmpfs with `noexec,nodev` | `test_writable_rootfs_rejected`, `test_every_writable_target_is_bounded` |
| Host filesystem write via mounts | every input mount forced `:ro`; the single writable bind is the designated output dir, which must lie outside every input source (realpath-compared) | `test_input_mounts_readonly_and_sorted`; `outputs-inside-mount-source` refusal (container_exec) + `test_…outputs-inside…` |
| Host filesystem read beyond declared inputs | only declared mounts + /output exist in the container namespace; an unmounted root is rejected before launch | `unmounted-root:<section>` refusal (container_exec) |
| Mount-sourced path traversal / symlink escape | mount sources and roots are realpath-normalized before comparison; symlinked source resolves to its real target | `test_symlink_source_normalized_to_realpath` |
| Socket / docker-podman control-channel mount | a mount source that is a socket is rejected at validation | `test_host_socket_bind_rejected` |
| Resource-exhaustion as an escape assist | memory/cpus/pids/nofile limits + scratch bounds + time limit + output cap; exhaustion is ERROR (exit 32), never a truncated pass | `test_missing_limit_rejected`, `test_bad_limit_rejected`, `test_timeout_kills_hung_container`, `test_output_overflow_kills_not_truncates` |
| Image substitution (running different bytes than pinned) | digest-qualified ref required and cross-checked against the registry; ref/digest mismatch fails closed | `test_bad_identity_digest_fields_rejected`, ref-digest-mismatch refusal (container_exec), A7 row |

Host-level facts this table stands on (measured 2026-09-26): both runner
hosts run **rootless podman** (`Rootless: true` on ucs03 and dell-u2), so
even a successful in-container escape lands in an unprivileged user
namespace, not root; and the hub binds its published ports to 127.0.0.1 and
the tailnet IP only — never 0.0.0.0 on the LAN interface. Residual,
deliberately honest: no seccomp profile beyond podman's rootless default,
no SELinux/AppArmor policy of our own, and user-namespace breakout bugs in
the kernel are out of scope for a repo-level control set — they are the
host's patch cadence, not the gate's.

## Known-uncovered surface (honest list)

- Key management is a symmetric stand-in (ADR-018 open): no HSM/KMS, no
  asymmetric separation of signing vs verification keys.
- The published evaluator image identity is OPEN (digest mismatch vs the
  registry is notice-only until the S4 publish retires it).
- External review of this service has not happened; this document and its
  test matrix are the prep package for that review (see MAINTAINERS.md).
