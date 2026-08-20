"""resumable_iterate() - checkpoint-free-of-boilerplate looping over a list.

Covers the common case (process each item in a list, resume where you left
off) with zero manual state bookkeeping - checkpoint() still runs underneath,
but you never call it or shape a state dict yourself.
"""
from .core import checkpoint, load_latest


def resumable_iterate(items, run_id: str, note=None):
    """Yield items one at a time; checkpoints (and resumes) automatically.

    `note` is an optional function(item) -> str for the waypoint's human note.

    At-least-once, not exactly-once: an item's checkpoint only fires once
    the loop asks for the *next* item (that's the only way a generator can
    tell you finished with the current one). If a crash happens right after
    you finish processing an item but before the loop moves on, that one
    item gets reprocessed on resume - never more than one, and never a
    half-processed item, but idempotent processing is still worth having if
    that matters for your task.
    """
    items = list(items)

    prior = load_latest(run_id)
    start_at = prior[0].get("_i", 0) if prior is not None else 0

    for i in range(start_at, len(items)):
        item = items[i]
        yield item
        default_note = f"processed item {i + 1}/{len(items)}"
        checkpoint(run_id, {"_i": i + 1}, note(item) if note else default_note)
