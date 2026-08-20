"""Scratch space - edit YOUR_WORK below, then run me, kill me (Ctrl+C)
partway through, run me again. Not a polished example (see examples/ for
those) - this is meant to be edited freely.

Setup once: pip install -e .   (from the repo root)
"""
from caravanserai import resumable_iterate

RUN_ID = "playground"


def your_items():
    """Replace this with whatever list you actually want to process."""
    return [f"item-{i}" for i in range(1, 21)]


def your_work(item):
    """Replace this with the actual thing you want done per item -
    an LLM call, a file operation, whatever. Keep the print so you can
    see progress; the time.sleep is just so you have time to Ctrl+C."""
    import time

    print(f"working on {item}...")
    time.sleep(1)
    print(f"  done: {item}")


if __name__ == "__main__":
    for item in resumable_iterate(your_items(), run_id=RUN_ID):
        your_work(item)
    print("all done.")

    # to start over instead of resuming: caravanserai clean playground
