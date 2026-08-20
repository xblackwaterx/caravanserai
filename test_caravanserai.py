"""Self-check: does the crash/resume promise actually work?

ponytail: one runnable check for the core non-trivial logic, no framework.
"""
import json
import shutil
import sys
from pathlib import Path

from caravanserai import checkpoint, clean, load_command, load_latest, resumable, resumable_iterate

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


def test_checkpoint_rejects_path_traversal_run_id():
    setup()
    for bad in ["../evil", "..\\evil", "a/../../etc", "/etc/passwd", ".."]:
        try:
            checkpoint(bad, {}, "note")
            assert False, f"should have rejected run_id={bad!r}"
        except ValueError:
            pass


def test_resumable_iterate_resumes_after_confirmed_items_only():
    setup()
    items = ["a", "b", "c", "d"]

    processed = []
    for item in resumable_iterate(items, RUN_ID):
        processed.append(item)
        if item == "c":
            break  # crash right after consuming "c" - its checkpoint hasn't
            # fired yet (a generator only learns "consumer is done with item i"
            # when next() is called for item i+1), so "c" is at-least-once,
            # not exactly-once: it gets redone on resume, "a" and "b" don't.

    assert processed == ["a", "b", "c"]

    # resuming: a and b are confirmed done, c was interrupted mid-confirmation
    resumed = list(resumable_iterate(items, RUN_ID))
    assert resumed == ["c", "d"]


def test_checkpoint_records_command_for_resume():
    setup()
    checkpoint(RUN_ID, {"step": 1}, "note")
    command = load_command(RUN_ID)
    assert command is not None
    # must include the interpreter, not just argv - argv[0] alone isn't
    # directly executable (this exact bug shipped once, caught by a real
    # clean-venv test run, not by this unit test - see git history)
    assert command == [sys.executable] + sys.argv


def test_clean_deletes_checkpoints():
    setup()
    checkpoint(RUN_ID, {"step": 1}, "note")
    assert load_latest(RUN_ID) is not None
    assert clean(RUN_ID) is True
    assert load_latest(RUN_ID) is None
    assert clean(RUN_ID) is False  # nothing left to delete, second time


def test_checkpoint_rejects_non_json_serializable_state():
    setup()
    try:
        checkpoint(RUN_ID, {"bad": {1, 2, 3}}, "note")  # a set isn't JSON-serializable
        assert False, "should have rejected a non-serializable state"
    except ValueError as e:
        assert "JSON-serializable" in str(e)


if __name__ == "__main__":
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
