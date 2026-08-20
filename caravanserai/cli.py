"""caravanserai list|show|resume|clean <run_id> - manage checkpoints from the terminal.

ponytail: argparse from stdlib, no click/typer needed for 4 subcommands.
"""
import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .core import clean, last_updated, load_command, load_latest

ROOT = Path(".caravanserai")


def _age(mtime) -> str:
    if mtime is None:
        return "?"
    seconds = datetime.now(timezone.utc).timestamp() - mtime
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    return f"{int(seconds / 86400)}d ago"


def cmd_list(_args):
    if not ROOT.exists():
        print("no runs yet")
        return
    for run_dir in sorted(ROOT.iterdir()):
        latest = run_dir / "latest"
        n = latest.read_text().strip() if latest.exists() else "0"
        print(f"{run_dir.name}\t{n} waypoint(s)\t{_age(last_updated(run_dir.name))}")


def cmd_show(args):
    result = load_latest(args.run_id)
    if result is None:
        print(f"no checkpoints for run '{args.run_id}'")
        return
    state, note, n = result
    print(f"waypoint {n}\n\n{note}\n\nstate: {state}")


def cmd_resume(args):
    command = load_command(args.run_id)
    if command is None:
        print(f"no checkpoints for run '{args.run_id}' - nothing to resume")
        return
    print(f"resuming: {' '.join(command)}")
    sys.exit(subprocess.call(command))


def cmd_clean(args):
    if clean(args.run_id):
        print(f"deleted checkpoints for '{args.run_id}'")
    else:
        print(f"no checkpoints for run '{args.run_id}'")


def main():
    parser = argparse.ArgumentParser(prog="caravanserai")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    show = sub.add_parser("show")
    show.add_argument("run_id")
    show.set_defaults(func=cmd_show)

    resume = sub.add_parser("resume")
    resume.add_argument("run_id")
    resume.set_defaults(func=cmd_resume)

    clean_cmd = sub.add_parser("clean")
    clean_cmd.add_argument("run_id")
    clean_cmd.set_defaults(func=cmd_clean)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
