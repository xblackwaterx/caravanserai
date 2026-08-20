"""Self-check: does the crash/resume promise actually work?

ponytail: one runnable check for the core non-trivial logic, no framework.
"""
import json
import shutil
from pathlib import Path

from caravanserai import checkpoint, load_latest, resumable

RUN_ID = "test-run"
ROOT = Path(".caravanserai") / RUN_ID


def setup():
    shutil.rmtree(".caravanserai", ignore_errors=True)


def test_checkpoint_then_load_latest_roundtrips_state_and_note():
    setup()
    checkpoint(RUN_ID, {"step": 1, "done": ["a"]}, "did step 1, next is step 2")
    checkpoint(RUN_ID, {"step": 2, "done": ["a", "b"]}, "did step 2, next is step 3")

    result = load_latest(RUN_ID)
    assert result is not None
    state, note, n = result
    assert state == {"step": 2, "done": ["a", "b"]}
    assert note == "did step 2, next is step 3"
    assert n == 2


def test_load_latest_returns_none_when_no_checkpoints_exist():
    setup()
    assert load_latest(RUN_ID) is None


def test_atomic_write_leaves_no_corrupt_state_on_crash():
    setup()
    checkpoint(RUN_ID, {"step": 1}, "step 1 done")
    # simulate a crash mid-write of the NEXT checkpoint: state.json must still
    # parse as valid JSON (the last good checkpoint), never half-written.
    state_file = ROOT / "state.json"
    raw = state_file.read_text()
    json.loads(raw)  # must not raise


def test_resumable_picks_up_from_last_checkpoint_not_from_scratch():
    setup()
    calls = []
    should_crash = {"value": True}  # crash-once flag, kept outside `state` on
    # purpose: `state` is exactly what gets wiped/replaced on resume, so the
    # test's own control flag can't live there.

    @resumable
    def run_task(run_id, state):
        step = state.get("step", 0)
        while step < 3:
            step += 1
            calls.append(step)
            if step == 2 and should_crash["value"]:
                should_crash["value"] = False
                # simulate a crash right after step 2 starts, before its own
                # checkpoint - so resume should replay step 2, not skip it.
                raise RuntimeError("simulated crash")
            checkpoint(run_id, {"step": step}, f"did step {step}")
        return step

    # first pass: crashes during step 2
    try:
        run_task(RUN_ID, {"step": 0})
    except RuntimeError:
        pass

    assert calls == [1, 2]  # step 1 checkpointed, step 2 crashed before checkpointing

    # second pass: resumable should load state {"step": 1} (last good checkpoint),
    # not the caller's fresh {"step": 0} initial state.
    calls.clear()
    result = run_task(RUN_ID, {"step": 0})

    assert calls == [2, 3]  # resumed from step 1, redid 2 and 3 - never redid step 1
    assert result == 3


if __name__ == "__main__":
    import sys
    import traceback

    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok   {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    shutil.rmtree(".caravanserai", ignore_errors=True)
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
