"""Bounded, on-demand monitoring; no event consumer or task argument storage."""
import socket
import time
from datetime import datetime, timezone
from uuid import uuid4

from django.core.cache import cache
from kombu import Consumer, Producer, Queue

from . import app


CACHE_KEY = 'ops:celery-monitor:v2'
LOCK_KEY = 'ops:celery-monitor:refresh'
REFRESH_SECONDS = 15
SNAPSHOT_SECONDS = 300
TASK_LIMIT = 100
WORKER_LIMIT = 100
INSPECT_TIMEOUT = 0.75
QUEUE_LIMIT = 100


def empty_snapshot(error):
    return {
        'sampled_at': None, 'stale': True, 'task_limit': TASK_LIMIT,
        'workers': [], 'queues': [], 'errors': [error],
        'summary': dict.fromkeys(('online_workers', 'active', 'reserved', 'scheduled', 'queued')),
    }


def stale_snapshot(cached, error):
    data = dict(cached['data']) if cached else empty_snapshot(error)
    data['stale'] = True
    data['errors'] = list(dict.fromkeys([*data['errors'], error]))
    return data


def safe_task(task):
    started = task.get('time_start')
    return {
        'id': str(task.get('id') or '')[:128],
        'name': str(task.get('name') or '')[:1024],
        'time_start': started if isinstance(started, (int, float)) else None,
        'acknowledged': task.get('acknowledged') if isinstance(task.get('acknowledged'), bool) else None,
        'eta': str(task.get('eta') or '')[:64] or None,
        'routing_key': str(task.get('routing_key') or '')[:128] or None,
        'definition_id': None,
    }


def worker_rpc(connection, method, arguments=None, destination=None, timeout=INSPECT_TIMEOUT):
    """One bounded pidbox RPC, without Kombu's default unlimited publish retry.

    Use the same wire format as Celery control, but enforce an overall reply
    deadline (the stock inspect timeout restarts after every arriving reply).
    """
    mailbox = app.control.mailbox(connection)
    ticket = str(uuid4())
    queue = Queue(
        f'{ticket}.{mailbox.reply_exchange.name}', exchange=mailbox.reply_exchange,
        routing_key=ticket, durable=False, auto_delete=True, expires=10,
        message_ttl=5,
    )
    replies = {}

    def receive(body, message):
        if message.headers.get('ticket') != ticket or not isinstance(body, dict):
            return
        for name, snapshot in body.items():
            if len(replies) >= WORKER_LIMIT:
                break
            if isinstance(name, str) and isinstance(snapshot, dict):
                if destination and name not in destination:
                    continue
                if method == 'jms_monitor_snapshot' and 'active_count' not in snapshot:
                    continue
                replies[name] = snapshot

    with connection.channel() as channel:
        try:
            with Consumer(channel, queues=[queue], callbacks=[receive],
                          accept=mailbox.accept, no_ack=True):
                Producer(channel, auto_declare=False).publish(
                    {'method': method, 'arguments': arguments or {}, 'destination': destination,
                     'pattern': None, 'matcher': None, 'ticket': ticket,
                     'reply_to': {'exchange': mailbox.reply_exchange.name, 'routing_key': ticket}},
                    exchange=mailbox.exchange.name, declare=[mailbox.exchange],
                    headers={'clock': mailbox.clock.forward(), 'expires': time.time() + timeout},
                    serializer=mailbox.serializer, retry=False,
                )
                deadline = time.monotonic() + timeout
                while len(replies) < WORKER_LIMIT:
                    if destination and len(replies) >= len(destination):
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        connection.drain_events(timeout=remaining)
                    except socket.timeout:
                        break
        finally:
            # Match Celery's reply queue cleanup, including the Redis transport.
            channel.after_reply_message_received(queue.name)
    return replies


def inspect_workers(connection):
    return worker_rpc(connection, 'jms_monitor_snapshot')


def stop_worker_task(worker, task_id, mode):
    options = dict(app.conf.broker_transport_options or {})
    options.update(socket_timeout=1, socket_connect_timeout=1, retry_on_timeout=False)
    try:
        with app.connection_for_read(connect_timeout=1, transport_options=options) as connection:
            connection.ensure_connection(max_retries=0)
            replies = worker_rpc(connection, 'jms_stop_task',
                                 {'task_id': task_id, 'mode': mode}, [worker], timeout=5)
    except Exception:
        return 'unavailable'
    response = replies.get(worker, {})
    status = response.get('status')
    allowed = {'revoked', 'revoke_requested', 'termination_requested', 'invalid',
               'not_found', 'unsupported_queue', 'unsupported_pool',
               'already_running', 'not_running', 'unavailable'}
    return status if status in allowed else 'unavailable'


def queue_depths(connection, names):
    """One Redis pipeline for all queues and their priority buckets (LLEN only)."""
    if connection.transport.driver_type != 'redis':
        return [{'name': name, 'pending': None} for name in names]
    with connection.channel() as channel:
        priorities = channel.priority_steps
        with channel.conn_or_acquire() as client:
            with client.pipeline() as pipe:
                for name in names:
                    for priority in priorities:
                        pipe.llen(channel._q_for_pri(name, priority))
                lengths = pipe.execute()
        width = len(priorities)
        return [{'name': name, 'pending': sum(lengths[index * width:(index + 1) * width])}
                for index, name in enumerate(names)]


def collect_snapshot(previous=None):
    errors = []
    replies = {}
    queue_names = set(app.amqp.queues)
    queues = []
    options = dict(app.conf.broker_transport_options or {})
    options.update(socket_timeout=1, socket_connect_timeout=1, retry_on_timeout=False)
    try:
        with app.connection_for_read(connect_timeout=1, transport_options=options) as connection:
            connection.ensure_connection(max_retries=0)
            try:
                replies = inspect_workers(connection)
            except Exception:
                errors.append('inspection_failed')
            for snapshot in replies.values():
                queue_names.update(q for q in snapshot.get('queues', [])[:QUEUE_LIMIT] if isinstance(q, str))
                if snapshot.get('queues_truncated'):
                    errors.append('queue_depth_failed')
            try:
                queues = queue_depths(connection, sorted(queue_names)[:QUEUE_LIMIT])
            except Exception:
                errors.append('queue_depth_failed')
    except Exception:
        errors.extend(('inspection_failed', 'queue_depth_failed'))

    if not queues:
        queues = [{'name': name, 'pending': None} for name in sorted(queue_names)[:QUEUE_LIMIT]]
    if len(queue_names) > QUEUE_LIMIT or any(q['pending'] is None for q in queues):
        errors.append('queue_depth_failed')
    online = set(replies)
    previous_workers = {worker['name']: worker for worker in (previous or {}).get('workers', [])}
    names = sorted(online)[:WORKER_LIMIT]
    names += sorted(set(previous_workers) - online)[:max(0, WORKER_LIMIT - len(names))]
    workers = []
    totals = {'online_workers': len(online), 'active': 0, 'reserved': 0, 'scheduled': 0}
    for name in names:
        snapshot = replies.get(name, {})
        worker = {
            'name': name, 'status': 'online' if name in online else 'unavailable',
            'concurrency': snapshot.get('concurrency'), 'processed': snapshot.get('processed'),
            'pool': snapshot.get('pool') if snapshot.get('pool') in ('threads', 'prefork') else 'unknown',
            'queues': snapshot.get('queues', [])[:QUEUE_LIMIT], 'truncated': {},
        }
        for field in ('active', 'reserved', 'scheduled'):
            tasks = snapshot.get(field, [])
            count = snapshot.get(field + '_count')
            if not isinstance(count, int) or count < 0:
                count = None
            worker[field + '_count'] = count
            worker['truncated'][field] = snapshot.get('truncated', {}).get(field, False)
            worker[field] = [safe_task(task) for task in tasks[:TASK_LIMIT] if isinstance(task, dict)]
            if name in online:
                if count is None:
                    totals[field] = None
                    errors.append('inspection_failed')
                elif totals[field] is not None:
                    totals[field] += count
        workers.append(worker)
    if not online:
        errors.append('no_workers')
        totals.update(active=None, reserved=None, scheduled=None)
    if len(online) >= WORKER_LIMIT:
        errors.append('inspection_failed')
        totals.update(online_workers=None, active=None, reserved=None, scheduled=None)
    totals['queued'] = sum(q['pending'] for q in queues) if queues and 'queue_depth_failed' not in errors and all(
        isinstance(q['pending'], int) for q in queues
    ) else None

    # Resolve only the bounded list shown by the UI. Never load task bodies,
    # parameters, execution history, broker URLs, or worker configuration here.
    from ops.models import CeleryTask
    task_names = {task['name'] for worker in workers for field in ('active', 'reserved', 'scheduled')
                  for task in worker[field]}
    definitions = dict(CeleryTask.objects.filter(name__in=task_names).values_list('name', 'id'))
    for worker in workers:
        for field in ('active', 'reserved', 'scheduled'):
            for task in worker[field]:
                definition_id = definitions.get(task['name'])
                task['definition_id'] = str(definition_id) if definition_id else None
    return {
        'sampled_at': datetime.now(timezone.utc).isoformat(),
        'stale': bool(errors), 'task_limit': TASK_LIMIT,
        'workers': workers, 'queues': queues, 'summary': totals,
        'errors': list(dict.fromkeys(errors)),
    }


def get_monitor_snapshot():
    cached = None
    lock = None
    acquired = False
    try:
        cached = cache.get(CACHE_KEY)
        if cached and time.time() - cached['collected_at'] < REFRESH_SECONDS:
            return cached['data']
        lock = cache.lock(LOCK_KEY, expire=30)
        acquired = lock.acquire(blocking=False)
        if not acquired:
            return stale_snapshot(cached, 'refresh_in_progress')
        # Another request may have published between our read and lock acquisition.
        latest = cache.get(CACHE_KEY)
        if latest and time.time() - latest['collected_at'] < REFRESH_SECONDS:
            return latest['data']
        data = collect_snapshot((latest or cached or {}).get('data'))
        cache.set(CACHE_KEY, {'collected_at': time.time(), 'data': data}, SNAPSHOT_SECONDS)
        return data
    except Exception:
        return stale_snapshot(cached, 'inspection_failed')
    finally:
        if acquired:
            try:
                lock.release()
            except Exception:
                pass
