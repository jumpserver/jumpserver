"""Bounded worker snapshots and targeted task control without task arguments."""
from itertools import islice

from celery.worker import state as worker_state
from celery.worker.control import control_command, inspect_command
from celery.worker.request import Request


TASK_LIMIT = 100
SCAN_LIMIT = 10000
QUEUE_LIMIT = 100


def task_summary(request, scheduled=False):
    started = request.time_start
    delivery = request.delivery_info or {}
    routing_key = delivery.get('routing_key') if isinstance(delivery, dict) else None
    return {
        'id': str(request.id)[:128], 'name': str(request.name)[:1024],
        'time_start': started if isinstance(started, (int, float)) else None,
        'acknowledged': request.acknowledged,
        'eta': request.eta.isoformat() if scheduled and request.eta else None,
        'routing_key': routing_key[:128] if isinstance(routing_key, str) else None,
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


@control_command()
def jms_stop_task(state, task_id=None, mode=None, **kwargs):
    """Stop only a locally observed ordinary task, never an Ansible job."""
    if not isinstance(task_id, str) or not task_id or len(task_id) > 128:
        return {'status': 'invalid'}
    if mode not in ('waiting', 'running'):
        return {'status': 'invalid'}
    consumer = state.consumer
    request = worker_state.requests.get(task_id)
    if request is None:
        try:
            request = next((item for item in scheduled_requests(consumer.timer)
                            if item.id == task_id), None)
        except (AttributeError, TypeError, RuntimeError):
            return {'status': 'unavailable'}
    if request is None:
        return {'status': 'not_found'}
    delivery = request.delivery_info or {}
    name = getattr(request, '_type', request.name)
    if (not isinstance(delivery, dict) or delivery.get('routing_key') != 'celery'
            or getattr(request.task, 'queue', None) == 'ansible'
            or name in ('ops.tasks.run_ops_job', 'ops.tasks.run_ops_job_execution')):
        return {'status': 'unsupported_queue'}

    active = request in worker_state.active_requests or bool(request.time_start)
    pool = consumer.controller.pool
    prefork = type(pool).__module__ == 'celery.concurrency.prefork'
    if mode == 'running':
        if not active:
            return {'status': 'not_running'}
        if not prefork:
            return {'status': 'unsupported_pool'}
        if not request.worker_pid:
            return {'status': 'unavailable'}
        worker_state.revoked.add(task_id)
        request.terminate(pool, signal='SIGTERM')
        return {'status': 'termination_requested'}

    if active:
        return {'status': 'already_running'}
    result_ref = request._apply_result
    if result_ref is not None:
        result = result_ref()
        future = getattr(result, 'f', None)
        if future is not None:
            if not future.cancel():
                return {'status': 'already_running'}
            worker_state.revoked.add(task_id)
            request._announce_revoked('revoked', False, None, False)
            return {'status': 'revoked'}
        if not prefork:
            return {'status': 'unavailable'}
        # A prefork job may already be in the pool's input buffer. Celery will
        # terminate its child when it accepts the task if it cannot cancel it.
        worker_state.revoked.add(task_id)
        request.terminate(pool, signal='SIGTERM')
        return {'status': 'termination_requested'}
    worker_state.revoked.add(task_id)
    return {'status': 'revoke_requested'}


@inspect_command()
def jms_monitor_snapshot(state, **kwargs):
    consumer = state.consumer
    active = worker_state.active_requests
    pool_module = type(consumer.controller.pool).__module__
    pool = {'celery.concurrency.thread': 'threads',
            'celery.concurrency.prefork': 'prefork'}.get(pool_module, 'unknown')
    result = {
        'concurrency': consumer.controller.concurrency,
        'pool': pool,
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
