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

Works with any Python agent loop you control — LangChain, LangGraph, the
Claude Agent SDK, OpenAI Agents SDK, CrewAI, or plain scripts. No database,
no server, just local JSON + Markdown files.

**Not for the Claude Code CLI itself** — it already has its own session
resume (`--resume`/`--continue`) and you don't write its agent loop. This is
for agents *you* build in Python that don't have that built in.

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

### Real transcript (not staged)

```
$ python demo.py
[1/5] doing work...
[2/5] doing work...
[3/5] doing work...
^C
crashed/killed mid-task. run me again — I'll resume, not restart.

$ python demo.py
[4/5] doing work...
[5/5] doing work...
done.

$ caravanserai show demo
waypoint 5

finished step 5/5

state: {'step': 5}
```

Killed at step 3, resumed straight to step 4 — no restart, no redone work.

## Status

v1 — explicit checkpoint calls only (no auto-detection), single-process local
files (no distributed state), inspect-only CLI (real resume path is
`@resumable` in your own code). See the design notes for what's deliberately
scoped out.
