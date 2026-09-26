"""Platform capability probes: SKIP what cannot run here, never let it fail.

A test that cannot run on this host must skip. The failure it would raise —
FileNotFoundError for a missing bash, PermissionError for a symlink without
the privilege, a digest filename mangled by the colon rule — is not evidence
about the code under test, and a red test nobody can act on trains people to
ignore red. That is the whole point: the signal a Windows developer reads has
to mean something, which means a missing capability has to be visible as a
skip with a reason, not as a failure.

Each probe is measured, not assumed. `has_symlink` tries to make a symlink,
`posix_readonly_dir` tries to make a directory unwritable and to write into
it, `case_sensitive_fs` tries to create two names differing only in case.
Windows answers each of these differently from Linux, and "probably not
supported" is not good enough when the answer costs one syscall.
"""
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def skip(reason: str):
    """Skip the running test. Works under pytest and unittest alike —
    unittest.SkipTest is what `skipTest` raises and pytest honours it, so a
    fixture or a plain function can call this without knowing which runner
    it is under."""
    raise unittest.SkipTest(reason)


def has_bash() -> bool:
    return _which("bash") is not None


def require_bash(what: str):
    if not has_bash():
        skip(f"{what}: needs bash on PATH (absent on this host)")


def _which(name: str):
    from shutil import which
    return which(name)


def has_symlink() -> bool:
    """Measured once per process: can this host create a symlink at all?

    Windows refuses os.symlink without the SeCreateSymbolicLink privilege
    unless Developer Mode is on, so the answer is a property of the MACHINE,
    not of the platform name. A Windows box with Developer Mode must be able
    to run these tests.
    """
    global _SYMLINK
    if _SYMLINK is None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.write_text("x", encoding="utf-8")
            try:
                (Path(td) / "link").symlink_to(target)
                _SYMLINK = True
            except (OSError, NotImplementedError, AttributeError):
                _SYMLINK = False
    return _SYMLINK


_SYMLINK = None


def require_symlink(what: str):
    if not has_symlink():
        skip(f"{what}: needs symlink creation (refused on this host — "
             "Windows wants Developer Mode or SeCreateSymbolicLink)")


def has_af_unix() -> bool:
    return hasattr(socket, "AF_UNIX")


def require_af_unix(what: str):
    if not has_af_unix():
        skip(f"{what}: needs a unix-domain socket (socket.AF_UNIX is absent "
             "on this host's Python build)")


def posix_readonly_dir(tmp: Path) -> bool:
    """Does chmod 0o555 actually make this directory unwritable HERE?

    Linux enforces the mode bit. Windows maps a directory's read-only ATTRIBUTE
    to something that does not stop writes into it, so a test that asserts
    'an unwritable outputs directory must yield exit 33' can only prove itself
    on the former. Measured, not assumed: chmod, then try to create a file.
    """
    d = tmp / "ro-probe"
    d.mkdir()
    os.chmod(d, 0o555)
    try:
        (d / "canary").write_text("x", encoding="utf-8")
        return False
    except OSError:
        return True
    finally:
        os.chmod(d, 0o755)
        for p in (d / "canary",):
            if p.exists():
                p.unlink()
        d.rmdir()


def require_posix_readonly_dir(what: str):
    with tempfile.TemporaryDirectory() as td:
        enforced = posix_readonly_dir(Path(td))
    if not enforced:
        skip(f"{what}: needs a chmod-enforced read-only directory "
             "(Windows does not enforce the mode bit on directories)")


def case_sensitive_fs(tmp: Path) -> bool:
    """Can two files in one directory differ only in letter case?

    A casefold COLLISION is the fixture several suites use to build an
    unbuildable tree. On a case-insensitive volume (NTFS by default) the
    second write silently replaces the first, so the collision cannot be
    constructed and the assertion under test cannot be reached.
    """
    d = tmp / "case-probe"
    d.mkdir()
    (d / "A.md").write_text("a", encoding="utf-8")
    (d / "a.md").write_text("b", encoding="utf-8")
    return sorted(p.name for p in d.iterdir()) == ["A.md", "a.md"]


def require_case_sensitive_fs(what: str):
    with tempfile.TemporaryDirectory() as td:
        ok = case_sensitive_fs(Path(td))
    if not ok:
        skip(f"{what}: needs a case-sensitive filesystem (this volume folds "
             "case, so a casefold collision cannot be constructed)")


def colon_in_filename_ok(tmp: Path) -> bool:
    """Can a bare 'sha256:<64 hex>' be a file NAME here?

    ':' is a stream separator in the Win32 path layer, so 'sha256:abc...' is
    an ALTERNATE DATA STREAM on a file called 'sha256' — it writes, it lists
    as 'sha256', and is_file() on the full name is False. A store that names
    its bundles and cache entries by digest ref therefore cannot be exercised
    on Windows at all: read() correctly reports retention-unknown for a bundle
    it can see no name for. The layout is the contract; the tests that read it
    are the ones that skip.
    """
    d = tmp / "colon-probe"
    d.mkdir()
    name = "sha256:" + "a" * 64
    p = d / name
    try:
        p.write_bytes(b"x")
    except OSError:
        return False
    return p.is_file() and [q.name for q in d.iterdir()] == [name]


def require_colon_in_filename(what: str):
    with tempfile.TemporaryDirectory() as td:
        ok = colon_in_filename_ok(Path(td))
    if not ok:
        skip(f"{what}: needs 'sha256:<hex>' to be a usable file name (this "
             "host treats the colon as an NTFS stream separator, so a "
             "digest-named store is not addressable)")


_LONG_CMDLINE = None


def has_long_command_line() -> bool:
    """Can CreateProcess take a command line longer than 32K?

    The runaway-output test passes its bomb to `python -c`; Windows caps the
    whole command line at 32767 characters and CreateProcess fails before the
    process exists, so there is no output to cap. (This is a property of the
    process API, not of the test's intent.)
    """
    global _LONG_CMDLINE
    if _LONG_CMDLINE is None:
        try:
            # Well past the 32767-character cap, so a host that enforces it
            # refuses (OSError) and a host that does not, runs it.
            subprocess.run(
                [sys.executable, "-c", "pass", *(["#" * 1024] * 40)],
                capture_output=True, timeout=60)
            _LONG_CMDLINE = True
        except OSError:
            _LONG_CMDLINE = False
    return _LONG_CMDLINE


def require_long_command_line(what: str):
    if not has_long_command_line():
        skip(f"{what}: needs a command line longer than 32K (CreateProcess "
             "caps it at 32767, so the process is never created)")


def has_posix_path_spelling() -> bool:
    """Does this host spell and resolve paths the way a Linux runtime does?

    The podman launcher derives `-v source:target` binds from HOST paths and
    hands them to a container: on Windows os.path.realpath('/srv/a') answers
    'C:\\srv\\a' and Path('/tmp/out') spells '\\tmp\\out', so the argv the
    launcher builds is not the argv a container runtime would ever receive.
    Measured rather than assumed — the two calls below are the product's own.
    """
    return str(Path("/a/b")) == "/a/b" and os.path.realpath("/srv/x") == "/srv/x"


def require_posix_path_spelling(what: str):
    if not has_posix_path_spelling():
        skip(f"{what}: needs POSIX path spelling (this host resolves "
             "'/srv/x' to a drive-lettered path, so the derived podman "
             "arguments are not the ones a container runtime would see)")


def has_resource_module() -> bool:
    """scripts/resource_audit.py measures child CPU with `resource` (POSIX)."""
    try:
        __import__("resource")
    except ImportError:
        return False
    return True


def require_resource_module(what: str):
    if not has_resource_module():
        skip(f"{what}: needs the POSIX `resource` module (absent on Windows)")


def has_fcntl() -> bool:
    try:
        __import__("fcntl")
    except ImportError:
        return False
    return True


def require_fcntl(what: str):
    if not has_fcntl():
        skip(f"{what}: needs fcntl (POSIX advisory locks; absent on Windows)")
