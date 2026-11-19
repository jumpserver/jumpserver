# -*- coding: utf-8 -*-
#
import json

import redis
import redis_lock
from django.conf import settings
from django.db.utils import ProgrammingError, OperationalError
from django.utils.timezone import get_current_timezone
from django.utils.translation import gettext
from django_celery_beat.models import (
    PeriodicTask, IntervalSchedule, CrontabSchedule, PeriodicTasks
)

from common.utils import get_logger
from common.utils.timezone import local_now

logger = get_logger(__name__)


def create_or_update_celery_periodic_tasks(tasks):
    """
    :param tasks: {
        'add-every-monday-morning': {
            'task': 'tasks.add' # A registered celery task,
            'interval': 30,
            'crontab': "30 7 * * *",
            'args': (16, 16),
            'kwargs': {},
            'enabled': False,
            'description': ''
        },
    }
    :return:
    """
    # Todo: check task valid, task and callback must be a celery task
    for name, detail in tasks.items():
        logger.info(gettext('Checking periodic task: %(name)s.'), {'name': name})
        interval = None
        crontab = None
        last_run_at = None

        try:
            IntervalSchedule.objects.all().count()
        except (ProgrammingError, OperationalError):
            logger.warning(gettext(
                'Skipped periodic task %(name)s: the scheduling database is unavailable.'
            ), {'name': name})
            return None

        if isinstance(detail.get("interval"), int):
            kwargs = dict(
                every=detail['interval'],
                period=IntervalSchedule.SECONDS,
            )
            # 不能使用 get_or_create，因为可能会有多个
            interval = IntervalSchedule.objects.filter(**kwargs).first()
            if interval is None:
                interval = IntervalSchedule.objects.create(**kwargs)
            last_run_at = local_now()
            logger.info(gettext('Schedule: every %(seconds)s seconds.'), {'seconds': detail['interval']})
        elif isinstance(detail.get("crontab"), str):
            try:
                minute, hour, day, month, week = detail["crontab"].split()
            except ValueError:
                logger.error(gettext(
                    'Skipped periodic task %(name)s: the cron expression must contain five fields.'
                ), {'name': name})
                return
            kwargs = dict(
                minute=minute, hour=hour, day_of_week=week,
                day_of_month=day, month_of_year=month, timezone=get_current_timezone()
            )
            crontab = CrontabSchedule.objects.filter(**kwargs).first()
            if crontab is None:
                crontab = CrontabSchedule.objects.create(**kwargs)
            logger.info(gettext('Schedule (cron): %(cron)s; time zone: %(timezone)s.'), {
                'cron': detail['crontab'], 'timezone': str(get_current_timezone()),
            })
        else:
            logger.warning(gettext(
                'Skipped periodic task %(name)s: no valid interval or cron expression is configured.'
            ), {'name': name})
            return

        defaults = dict(
            interval=interval,
            crontab=crontab,
            name=name,
            task=detail['task'],
            args=json.dumps(detail.get('args', [])),
            kwargs=json.dumps(detail.get('kwargs', {})),
            description=detail.get('description') or '',
            last_run_at=last_run_at,
        )
        enabled = detail.get('enabled')
        if enabled is not None:
            defaults["enabled"] = enabled
        task = PeriodicTask.objects.update_or_create(
            defaults=defaults, name=name,
        )
        PeriodicTasks.update_changed()
        instance, created = task
        if created:
            message = gettext('Created periodic task %(name)s; enabled: %(enabled)s.')
        else:
            message = gettext('Updated periodic task %(name)s; enabled: %(enabled)s.')
        logger.info(message, {
            'name': name,
            'enabled': gettext('Yes') if instance.enabled else gettext('No'),
        })
        return task


def disable_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    count = PeriodicTask.objects.filter(name=task_name).update(enabled=False)
    PeriodicTasks.update_changed()
    return count


def delete_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(name=task_name).delete()
    PeriodicTasks.update_changed()


def get_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    task = PeriodicTask.objects.filter(name=task_name).first()
    return task


def get_celery_task_log_path(task_id):
    from ops.utils import get_task_log_path
    return get_task_log_path(settings.CELERY_LOG_DIR, task_id)


def get_celery_status():
    from . import app
    i = app.control.inspect()
    ping_data = i.ping() or {}
    active_nodes = [k for k, v in ping_data.items() if v.get('ok') == 'pong']
    active_queue_worker = set([n.split('@')[0] for n in active_nodes if n])
    # Celery Worker 数量: 2
    if len(active_queue_worker) < 2:
        print("Not all celery worker worked")
        return False
    else:
        return True


def get_beat_status():
    CONFIG = settings.CONFIG
    r = redis.Redis(host=CONFIG.REDIS_HOST, port=CONFIG.REDIS_PORT, password=CONFIG.REDIS_PASSWORD)
    lock = redis_lock.Lock(r, name="beat-distribute-start-lock")
    try:
        locked = lock.locked()
        return locked
    except redis.ConnectionError:
        return False
