# Caravanserai

[![PyPI](https://img.shields.io/pypi/v/caravanserai)](https://pypi.org/project/caravanserai/)
[![Python](https://img.shields.io/pypi/pyversions/caravanserai)](https://pypi.org/project/caravanserai/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## The idea, before the code

For a thousand years, caravans crossing the Silk Road never made the journey
from Samarkand to Xi'an in one unbroken push. They couldn't — no camel, no
person, survives that. Instead the route was strung with **caravanserai**:
walled waystations spaced a day's travel apart. A caravan arrived, rested,
traded news with whoever else was passing through, and the next morning
someone — often not the same person — picked the journey back up from
exactly where the last leg ended. The road didn't care who carried the load
across any one stretch. It only cared that the relay never lost its place.

A long-running AI agent has the same problem and none of the same
infrastructure. It runs for hours, hits a crash, a rate limit, a killed
process — and unlike the caravan, there's no waystation. Everything since
the last save is just gone. Worse: even when a framework *does* checkpoint,
what it leaves behind is a raw state blob — readable by a resume function,
unreadable by you or by whichever agent instance picks the job back up next.

Caravanserai is the waystation. Your agent checkpoints at natural stopping
points, saving both its exact state *and* a plain-English note — what
happened, what's next — the way a courier arriving at a real caravanserai
would report the state of the road to whoever rides out next.

## Quickstart

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

## How a checkpoint works

```
  your agent loop
        │
        ▼
   step 1 ──► checkpoint() ──► .caravanserai/<run_id>/
        │                        ├── state.json       (exact state, atomic write)
        │                        ├── waypoint-1.md     (human-readable note)
        │                        └── latest            (pointer → 1)
        ▼
   step 2 ──► checkpoint() ──► waypoint-2.md, latest → 2
        │
        ✕  crash / kill / rate limit
        │
   re-run with same run_id
        │
        ▼
   @resumable loads latest ──► state = {step: 2} ──► continues from step 3
```

A waypoint file looks like this — meant to be read, by a person or by a
different agent picking up the same job:

```
.caravanserai/my-run/waypoint-3.md
# Waypoint 3 — 2026-08-20T22:41:03+00:00

finished step 3, next is step 4
```

## Why not just use LangGraph or Temporal?

| | Caravanserai | LangGraph checkpointing | Temporal |
|---|---|---|---|
| Framework lock-in | None — any Python loop | LangGraph only | Its own workflow engine |
| What's saved | State **+ a human-readable note** | Raw state snapshot only | Raw event history |
| Infra required | None — local files | None (or a DB backend) | A Temporal server/cluster |
| Setup for v1 use | `pip install`, call one function | Adopt LangGraph's graph model | Adopt Temporal's workflow model |
| Guarantees | Save/load state (this is v1 scope) | Full replay semantics | Full durable execution, replay, idempotency |

They solve the mechanical replay problem well and Temporal in particular
solves it far more rigorously than Caravanserai attempts to — this isn't a
durable-execution engine. What none of them do is leave behind something a
*human* can read at a glance to understand what the agent actually did. That
gap is the entire reason this exists.

## Try it yourself

```
pip install caravanserai
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
This was also verified against the actual published PyPI package, installed
fresh into an empty virtualenv, not just the dev source.

## Works with

Any Python agent loop you control — LangChain, LangGraph, the Claude Agent
SDK, OpenAI Agents SDK, CrewAI, or plain scripts. No database, no server,
just local JSON + Markdown files.

**Not for the Claude Code CLI itself** — it already has its own session
resume (`--resume`/`--continue`) and you don't write its agent loop. This is
for agents *you* build in Python that don't have that built in.

## Status

v1 — explicit checkpoint calls only (no auto-detection), single-process
local files (no distributed state), inspect-only CLI (the real resume path
is `@resumable` in your own code). Deliberately not attempting LangGraph/
Temporal-grade replay-with-re-execution semantics — save/load state is the
whole promise, kept simple on purpose.

## License

MIT — see [LICENSE](LICENSE).
