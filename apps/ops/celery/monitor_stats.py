"""Worker-lifetime outcome counters shared by thread and prefork pools.

Imported at worker_init, before the pool forks. Only three counters are kept;
task arguments, results and execution identifiers are never stored here.
"""
from ctypes import c_ulonglong

from billiard import Array, Value
from celery import signals


OUTCOME_FIELDS = ('succeeded', 'failed', 'retried')
_counts = Array(c_ulonglong, [0, 0, 0], lock=True)
_complete = Value('b', 1, lock=False)


def record_outcome(index, sender):
    if getattr(getattr(sender, 'request', None), 'is_eager', False):
        return
    lock = _counts.get_lock()
    if not lock.acquire(timeout=0.05):
        # Never delay task execution indefinitely if a child died holding the
        # lock. Incomplete counters must be displayed as unknown, not zero.
        _complete.value = 0
        return
    try:
        _counts[index] += 1
    finally:
        lock.release()


@signals.task_success.connect(weak=False)
def count_success(sender=None, **kwargs):
    record_outcome(0, sender)


@signals.task_failure.connect(weak=False)
def count_failure(sender=None, **kwargs):
    record_outcome(1, sender)


@signals.task_retry.connect(weak=False)
def count_retry(sender=None, **kwargs):
    record_outcome(2, sender)


def get_outcome_counts():
    unknown = dict.fromkeys(OUTCOME_FIELDS)
    if not _complete.value:
        return unknown
    lock = _counts.get_lock()
    if not lock.acquire(timeout=0.05):
        return unknown
    try:
        return dict(zip(OUTCOME_FIELDS, _counts[:])) if _complete.value else unknown
    finally:
        lock.release()
