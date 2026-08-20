"""checkpoint() and load_latest() - atomic JSON+Markdown waystation files.

ponytail: stdlib only, no DB. json.dumps + os.replace is all "atomic write" needs.
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
import os


def _run_dir(run_id: str) -> Path:
    # security: run_id can come from caller-controlled sources (task names,
    # ticket IDs) that might trace back to external input - reject anything
    # that could escape .caravanserai/ via path traversal or an absolute path.
    if not run_id or "/" in run_id or "\\" in run_id or run_id in (".", ".."):
        raise ValueError(f"invalid run_id: {run_id!r} (no path separators or '..' allowed)")
    return Path(".caravanserai") / run_id


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)  # atomic on POSIX and Windows


def checkpoint(run_id: str, state: dict, note: str) -> int:
    """Save a waystation: state.json (for the program) + waypoint-N.md (for a human).

    Returns the waypoint number just written.
    """
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        state_json = json.dumps(state, indent=2)
    except TypeError as e:
        raise ValueError(
            f"checkpoint() state must be JSON-serializable (plain dicts/lists/"
            f"str/int/float/bool/None) - got: {e}"
        ) from e

    latest_file = run_dir / "latest"
    n = int(latest_file.read_text()) + 1 if latest_file.exists() else 1

    meta_file = run_dir / "meta.json"
    if not meta_file.exists():
        # record how this run was launched, once, so `caravanserai resume`
        # can replay it later without the caller wiring that up themselves.
        # sys.executable is required, not just sys.argv - argv[0] alone
        # (e.g. "myscript.py") isn't directly executable on Windows or on
        # Linux without a shebang; subprocess needs the interpreter too.
        command = [sys.executable] + sys.argv
        _atomic_write(meta_file, json.dumps({"command": command}, indent=2))

    _atomic_write(run_dir / "state.json", state_json)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _atomic_write(run_dir / f"waypoint-{n}.md", f"# Waypoint {n} - {ts}\n\n{note}\n")
    _atomic_write(latest_file, str(n))

    return n


def load_latest(run_id: str):
    """Return (state, note, n) from the last checkpoint, or None if none exist."""
    run_dir = _run_dir(run_id)
    latest_file = run_dir / "latest"
    if not latest_file.exists():
        return None

    n = int(latest_file.read_text())
    state = json.loads((run_dir / "state.json").read_text())
    waypoint_md = (run_dir / f"waypoint-{n}.md").read_text()
    note = waypoint_md.split("\n\n", 1)[1].strip()
    return state, note, n


def load_command(run_id: str):
    """Return the argv the run was originally launched with, or None."""
    meta_file = _run_dir(run_id) / "meta.json"
    if not meta_file.exists():
        return None
    return json.loads(meta_file.read_text())["command"]


def last_updated(run_id: str):
    """Return the mtime (float, seconds since epoch) of the latest checkpoint, or None."""
    latest_file = _run_dir(run_id) / "latest"
    if not latest_file.exists():
        return None
    return latest_file.stat().st_mtime


def clean(run_id: str) -> bool:
    """Delete a run's checkpoints entirely. Returns True if anything was deleted."""
    run_dir = _run_dir(run_id)
    if not run_dir.exists():
        return False
    shutil.rmtree(run_dir)
    return True
