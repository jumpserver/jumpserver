"""Worker-side, read-only snapshots with bounded output and no task arguments."""
from itertools import islice

from celery.worker import state as worker_state
from celery.worker.control import inspect_command
from celery.worker.request import Request


TASK_LIMIT = 100
SCAN_LIMIT = 10000
QUEUE_LIMIT = 100


def task_summary(request, scheduled=False):
    started = request.time_start
    return {
        'id': str(request.id)[:128], 'name': str(request.name)[:1024],
        'time_start': started if isinstance(started, (int, float)) else None,
        'acknowledged': request.acknowledged,
        'eta': request.eta.isoformat() if scheduled and request.eta else None,
    }


def summarize(requests, scheduled=False, exclude=None):
    tasks, count = [], 0
    try:
        for index, request in enumerate(requests):
            if index >= SCAN_LIMIT:
                return tasks, None, True
            if exclude is not None and request in exclude:
                continue
            count += 1
            if len(tasks) < TASK_LIMIT:
                tasks.append(task_summary(request, scheduled))
    except RuntimeError:
        # Thread pools can finish tasks during WeakSet iteration. Do not publish
        # a partial count as an exact total or retry an unbounded number of times.
        return tasks, None, True
    return tasks, count, count > len(tasks)


def scheduled_requests(timer):
    # Celery's public schedule.queue sorts/copies the entire ETA heap. Inspect a
    # bounded prefix of that heap instead; output ordering is intentionally not
    # an ETA guarantee. This follows the pinned Kombu timer representation.
    heap = timer.schedule._queue
    for waiting in islice(heap, SCAN_LIMIT + 1):
        entry = waiting.entry
        if entry.canceled:
            continue
        args = entry.args
        if args and isinstance(args[0], Request):
            yield args[0]


@inspect_command()
def jms_monitor_snapshot(state, **kwargs):
    consumer = state.consumer
    active = worker_state.active_requests
    result = {
        'concurrency': consumer.controller.concurrency,
        'processed': worker_state.all_total_count[0],
        'queues': [q.name for q in islice(consumer.task_consumer.queues, QUEUE_LIMIT)],
        'queues_truncated': len(consumer.task_consumer.queues) > QUEUE_LIMIT,
        'truncated': {},
    }
    sources = {
        'active': (active, False, None),
        'reserved': (worker_state.reserved_requests, False, active),
    }
    for field, (requests, scheduled, exclude) in sources.items():
        tasks, count, truncated = summarize(requests, scheduled, exclude)
        result[field] = tasks
        result[field + '_count'] = count
        result['truncated'][field] = truncated
    try:
        tasks, count, truncated = summarize(scheduled_requests(consumer.timer), scheduled=True)
        if len(consumer.timer.schedule._queue) > SCAN_LIMIT:
            count, truncated = None, True
    except (AttributeError, TypeError, RuntimeError):
        # Unsupported timer implementations are unknown, never reported as zero.
        tasks, count, truncated = [], None, True
    result.update(scheduled=tasks, scheduled_count=count)
    result['truncated']['scheduled'] = truncated
    return result
