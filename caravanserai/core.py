"""checkpoint() and load_latest() — atomic JSON+Markdown waystation files.

ponytail: stdlib only, no DB. json.dumps + os.replace is all "atomic write" needs.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _run_dir(run_id: str) -> Path:
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

    latest_file = run_dir / "latest"
    n = int(latest_file.read_text()) + 1 if latest_file.exists() else 1

    _atomic_write(run_dir / "state.json", json.dumps(state, indent=2))
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _atomic_write(run_dir / f"waypoint-{n}.md", f"# Waypoint {n} — {ts}\n\n{note}\n")
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
