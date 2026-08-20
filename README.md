<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/xblackwaterx/caravanserai/master/assets/logo-dark.svg">
  <img alt="Caravanserai" src="https://raw.githubusercontent.com/xblackwaterx/caravanserai/master/assets/logo-light.svg" width="320">
</picture>

[![PyPI](https://img.shields.io/pypi/v/caravanserai?cacheSeconds=300)](https://pypi.org/project/caravanserai/)
[![Python](https://img.shields.io/pypi/pyversions/caravanserai?cacheSeconds=300)](https://pypi.org/project/caravanserai/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

<img alt="Caravanserai crashing mid-migration and resuming cleanly" src="https://raw.githubusercontent.com/xblackwaterx/caravanserai/master/assets/demo.svg" width="800">

*Real run, not staged - killed mid-file 4, resumed at file 4 automatically.
Full source: [`examples/migrate_files.py`](examples/migrate_files.py).*

## The idea, before the code

For a thousand years, caravans crossing the Silk Road never made the journey
from Samarkand to Xi'an in one unbroken push. They couldn't - no camel, no
person, survives that. Instead the route was strung with **caravanserai**:
walled waystations spaced a day's travel apart. A caravan arrived, rested,
traded news with whoever else was passing through, and the next morning
someone - often not the same person - picked the journey back up from
exactly where the last leg ended. The road didn't care who carried the load
across any one stretch. It only cared that the relay never lost its place.

A long-running AI agent has the same problem and none of the same
infrastructure. It runs for hours, hits a crash, a rate limit, a killed
process - and unlike the caravan, there's no waystation. Everything since
the last save is just gone. Worse: even when a framework *does* checkpoint,
what it leaves behind is a raw state blob - readable by a resume function,
unreadable by you or by whichever agent instance picks the job back up next.

Caravanserai is the waystation. Your agent checkpoints at natural stopping
points, saving both its exact state *and* a plain-English note - what
happened, what's next - the way a courier arriving at a real caravanserai
would report the state of the road to whoever rides out next.

## Quickstart

Looping over a list of things (files, tasks, rows)? Use `resumable_iterate` -
zero manual state bookkeeping:

```python
from caravanserai import resumable_iterate

for f in resumable_iterate(all_files(), run_id="my-run"):
    convert_file(f)
```

Kill it mid-run. Run it again - it picks up right where it left off, no
`checkpoint()` call, no state dict to design yourself. One caveat, honestly
stated: it's at-least-once, not exactly-once - the item you were mid-way
through when the crash happened may get reprocessed once (never more, never
half-processed), since a generator only learns you finished an item when the
loop asks for the next one. Fine for idempotent work; worth knowing if not.

For anything that isn't a flat list - a while-loop, a state machine, multiple
things changing per step - use `checkpoint()` + `@resumable` directly and
shape your own state dict:

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

Kill it mid-run. Run it again with the same `run_id` - `@resumable` loads the
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

A waypoint file looks like this - meant to be read, by a person or by a
different agent picking up the same job:

```
.caravanserai/my-run/waypoint-3.md
# Waypoint 3 - 2026-08-20T22:41:03+00:00

finished step 3, next is step 4
```

## Why not just use LangGraph or Temporal?

| | Caravanserai | LangGraph checkpointing | Temporal |
|---|---|---|---|
| Framework lock-in | None - any Python loop | LangGraph only | Its own workflow engine |
| What's saved | State **+ a human-readable note** | Raw state snapshot only | Raw event history |
| Infra required | None - local files | None (or a DB backend) | A Temporal server/cluster |
| Setup for v1 use | `pip install`, call one function | Adopt LangGraph's graph model | Adopt Temporal's workflow model |
| Guarantees | Save/load state (this is v1 scope) | Full replay semantics | Full durable execution, replay, idempotency |

They solve the mechanical replay problem well and Temporal in particular
solves it far more rigorously than Caravanserai attempts to - this isn't a
durable-execution engine. What none of them do is leave behind something a
*human* can read at a glance to understand what the agent actually did. That
gap is the entire reason this exists.

## User flow, end to end

A real example lives at [`examples/migrate_files.py`](examples/migrate_files.py) -
migrating 10 files with a per-file operation (stand-in for an LLM call).
Here's the actual flow, with output from a real run:

**1. Write the loop** - one import, one call, no state dict to design:
```python
from caravanserai import resumable_iterate

def all_js_files():
    return [f"module_{i}.js" for i in range(1, 11)]

for f in resumable_iterate(all_js_files(), run_id="js-to-ts-migration"):
    convert_file(f)  # your own logic - an LLM call, a slow operation, whatever
```

**2. Run it:**
```
$ python examples/migrate_files.py
  converting module_1.js...
  done: module_1.js
  converting module_2.js...
  done: module_2.js
  converting module_3.js...
```

**3. It dies mid-file 4** (crash, Ctrl+C, killed process - doesn't matter
which) - files 1-3 were fully processed and checkpointed already:
```
  converting module_4.js...
^C
```

**4. Check what happened without rerunning anything:**
```
$ caravanserai show js-to-ts-migration
waypoint 3

processed item 3/10

state: {'_i': 3}
```

**5. Run the exact same command again:**
```
$ python examples/migrate_files.py
  converting module_4.js...
  done: module_4.js
  converting module_5.js...
  ...
  converting module_10.js...
  done: module_10.js
migration complete.
```

No flags, no `--resume`, nothing to remember - it picked up at file 4 on its
own because the `run_id` matched. Files 1-3 were fully converted and
checkpointed before the crash, so they're skipped; file 4 was killed
mid-`convert_file`, so `_i` still says 3 done and file 4 runs again - see the
at-least-once caveat above for exactly when a file gets redone.

**6. Once you're done with a run, clean it up:**
```
$ caravanserai clean js-to-ts-migration
deleted checkpoints for 'js-to-ts-migration'
```

## CLI

```
caravanserai list                # every run, waypoint count, last-updated
caravanserai show <run_id>       # inspect the latest waypoint note + state
caravanserai resume <run_id>     # re-run the exact command that started it
caravanserai clean <run_id>      # delete a run's checkpoints
```

`resume` works because the first `checkpoint()` call for a run records the
command it was launched with (`sys.argv`) - `caravanserai resume` just
replays that command as a subprocess, so `@resumable` picks up from the last
checkpoint the normal way.

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
crashed/killed mid-task. run me again - I'll resume, not restart.

$ python demo.py
[4/5] doing work...
[5/5] doing work...
done.

$ caravanserai show demo
waypoint 5

finished step 5/5

state: {'step': 5}
```

Killed at step 3, resumed straight to step 4 - no restart, no redone work.
This was also verified against the actual published PyPI package, installed
fresh into an empty virtualenv, not just the dev source.

## Works with

Any Python agent loop you control - LangChain, LangGraph, the Claude Agent
SDK, OpenAI Agents SDK, CrewAI, or plain scripts. No database, no server,
just local JSON + Markdown files.

**Not for the Claude Code CLI itself** - it already has its own session
resume (`--resume`/`--continue`) and you don't write its agent loop. This is
for agents *you* build in Python that don't have that built in.

## Status

0.2.0 - `resumable_iterate` for the common list-processing case,
`checkpoint`/`@resumable` for everything else, a CLI that can actually
resume a run (not just inspect it). Still single-process local files only
(no distributed state), still no auto-detection of checkpoint intervals -
deliberately not attempting LangGraph/Temporal-grade replay-with-
re-execution semantics. Save/load state, kept simple on purpose.

## License

MIT - see [LICENSE](LICENSE).
