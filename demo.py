"""Run me, kill me mid-way (Ctrl+C), run me again — I pick up where I left off.

This is the literal script the README demo/gif is made from.
"""
import sys
import time

from caravanserai import checkpoint, resumable

RUN_ID = "demo"


@resumable
def do_the_task(run_id, state):
    step = state.get("step", 0)
    total = 5
    while step < total:
        step += 1
        print(f"[{step}/{total}] doing work...")
        time.sleep(1)
        checkpoint(run_id, {"step": step}, f"finished step {step}/{total}")
    print("done.")


if __name__ == "__main__":
    initial = {"step": 0}
    try:
        do_the_task(RUN_ID, initial)
    except KeyboardInterrupt:
        print("\ncrashed/killed mid-task. run me again — I'll resume, not restart.")
        sys.exit(1)
