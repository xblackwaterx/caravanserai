"""caravanserai list|show <run_id> — inspect checkpoints from the terminal.

ponytail: v1 CLI is inspect-only; @resumable in your own code is the real
resume path. argparse from stdlib, no click/typer needed for 2 subcommands.
"""
import argparse
from pathlib import Path

from .core import load_latest

ROOT = Path(".caravanserai")


def cmd_list(_args):
    if not ROOT.exists():
        print("no runs yet")
        return
    for run_dir in sorted(ROOT.iterdir()):
        latest = run_dir / "latest"
        n = latest.read_text().strip() if latest.exists() else "0"
        print(f"{run_dir.name}\t{n} waypoint(s)")


def cmd_show(args):
    result = load_latest(args.run_id)
    if result is None:
        print(f"no checkpoints for run '{args.run_id}'")
        return
    state, note, n = result
    print(f"waypoint {n}\n\n{note}\n\nstate: {state}")


def main():
    parser = argparse.ArgumentParser(prog="caravanserai")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    show = sub.add_parser("show")
    show.add_argument("run_id")
    show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
