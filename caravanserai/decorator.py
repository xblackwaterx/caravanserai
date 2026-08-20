"""@resumable - on crash, next call picks up from the last checkpoint."""
import functools

from .core import load_latest


def resumable(fn):
    """Wrap a function f(run_id, state, *a, **kw). If a checkpoint already
    exists for run_id, the caller's initial `state` is replaced with the
    last saved state before fn runs.
    """

    @functools.wraps(fn)
    def wrapper(run_id, state, *args, **kwargs):
        prior = load_latest(run_id)
        if prior is not None:
            state, _note, _n = prior
        return fn(run_id, state, *args, **kwargs)

    return wrapper
