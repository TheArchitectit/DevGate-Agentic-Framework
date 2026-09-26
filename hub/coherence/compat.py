"""Compatibility policy machinery for the wire contract (S8 tasks.md:1020).

The version gate (`__main__.run`'s protocol guard) refuses anything that is
not the currently emitted `SUPPORTED_API`. Refusing is the contract; what was
missing is the *distinction between kinds of refusal*. An operator whose hub
emits a retired version should hear "this version was retired on a recorded
date — upgrade the emitting side", not the same line a typo in the family
name produces. This module is the single home for that distinction:

  * `current()` — the version this build emits and judges (the same string
    `SUPPORTED_API` holds; the const stays in `__main__` as the emitter's
    truth, and this module derives its registry from it so the two cannot
    drift apart silently — `test_retired_registry_never_names_the_current_version`
    keeps the directions explicit).

  * `classify(api_version)` — `current`, `retired` (with the policy note
    naming its retirement), or `foreign` (anything else: never-existed,
    mistyped family, or a future version this build predates).

  * `retire(version, note)` — the write side, called by the release process
    when a version's deprecation window closes (the policy doc's Removal
    step). It refuses to retire the current version: retirement is defined
    against a *predecessor* — you first ship the new `SUPPORTED_API`, then
    retire the old one. The registry is code, under the same review as the
    gate itself; a retired version is a deliberate, reviewed act, not a
    config flip.
"""
from datetime import date

# family/version -> (retired_on, policy_note). Empty today: v1 is the first
# and only version of the contract, so nothing can be retired yet. The
# registry exists so the FIRST retirement is a data edit plus the policy
# doc's recorded window, not a redesign of the gate.
_RETIRED = {}


def current() -> str:
    """The wire version this build emits. Derived from the emitter's const
    (imported lazily to avoid an import cycle: __main__ imports this module
    for its gate)."""
    from hub.coherence.__main__ import SUPPORTED_API
    return SUPPORTED_API


def classify(api_version) -> tuple:
    """(status, detail) for a request-supplied api_version.

    status: "current" | "retired" | "foreign".
    detail: for retired, the retirement record (date + note); otherwise a
    short explanation suitable for the envelope reason.
    """
    cur = current()
    if api_version == cur:
        return ("current", "")
    if isinstance(api_version, str) and api_version in _RETIRED:
        retired_on, note = _RETIRED[api_version]
        return ("retired", (retired_on, note))
    return ("foreign",
            f"not the supported contract version {cur!r}")


def retired_note(api_version: str) -> str:
    """The envelope reason for a retired version: names the version, the
    retirement date, and the upgrade direction. Only callable for a version
    actually in the registry — the gate's classify() routes foreign versions
    to the generic refusal, never here."""
    retired_on, note = _RETIRED[api_version]
    return (f"api_version {api_version!r} was retired on {retired_on.isoformat()}"
            f"{f': {note}' if note else ''}; "
            f"upgrade the emitting side to {current()!r}")


_VERSION_SHAPE = __import__("re").compile(
    r"^[a-z0-9][a-z0-9.\-]*/v[0-9]+$")


def retire(version: str, *, retired_on: date, note: str = "") -> None:
    """Record a retirement. Refuses to retire the currently emitted version:
    retirement is a step that follows shipping a successor, never a way to
    turn the live contract off. Also refuses a version that is not a
    well-formed `<family>/vN` string and a date in the future — the registry
    is the evidence trail the runbook triage reads, so a record must not be
    able to misdescribe what it retired or when."""
    if version == current():
        raise ValueError(
            f"refusing to retire {version!r}: it is the currently emitted "
            f"version; ship the successor first")
    if not isinstance(version, str) or not _VERSION_SHAPE.match(version):
        raise ValueError(
            f"retired version {version!r} is not a `<family>/vN` string")
    if not isinstance(retired_on, date):
        raise TypeError("retired_on must be a datetime.date")
    if retired_on > date.today():
        raise ValueError(
            f"refusing to retire {version!r} effective {retired_on.isoformat()}: "
            f"the retirement date is in the future; retire when it happens, "
            f"not in advance")
    _RETIRED[version] = (retired_on, note)