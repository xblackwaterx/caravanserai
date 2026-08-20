# Caravanserai

Your AI agent just spent 3 hours on a task. It crashed. Everything's gone.

Caravanserai fixes that: your agent checkpoints itself at natural waypoints — like
a Silk Road caravan resting at a waystation — saving both its exact state *and*
a plain-English note of what happened and what's next. Crash, and the next run
picks up from the last waystation instead of starting over.

```python
from caravanserai import checkpoint, resumable

@resumable
def do_the_task(run_id, state):
    step = state.get("step", 0)
    while step < 5:
        step += 1
        # ... do the actual work ...
        checkpoint(run_id, {"step": step}, f"finished step {step}, next is step {step+1}")

do_the_task("my-run", {"step": 0})
```

Kill it mid-run. Run it again with the same `run_id` — `@resumable` loads the
last saved state automatically instead of starting from scratch.

## Why not just use LangGraph/Temporal checkpointing?

They solve the mechanical replay problem well, but they're framework-locked
and the checkpoint is a raw state blob — nothing a human (or a *different*
agent picking up the job) can read to understand what actually happened.
Caravanserai's waypoint files are markdown, meant to be read:

```
.caravanserai/my-run/waypoint-3.md
# Waypoint 3 — 2026-08-20T22:41:03+00:00

finished step 3, next is step 4
```

Works with any Python agent loop — LangChain, OpenAI Agents SDK, or plain
scripts. No database, no server, just local JSON + Markdown files.

## Install

```
pip install -e .
```

## Try it

```
python demo.py
# ^C it partway through, then:
python demo.py
# picks up where it left off
caravanserai show demo
```

## Status

v1 — explicit checkpoint calls only (no auto-detection), single-process local
files (no distributed state), inspect-only CLI (real resume path is
`@resumable` in your own code). See the design notes for what's deliberately
scoped out.
