# -*- coding: utf-8 -*-
#
import json
import os

from django.conf import settings
from django.utils.timezone import get_current_timezone
from django.db.utils import ProgrammingError, OperationalError
from django_celery_beat.models import (
    PeriodicTask, IntervalSchedule, CrontabSchedule, PeriodicTasks
)

from common.utils import get_logger

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
        interval = None
        crontab = None
        try:
            IntervalSchedule.objects.all().count()
        except (ProgrammingError, OperationalError):
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
        elif isinstance(detail.get("crontab"), str):
            try:
                minute, hour, day, month, week = detail["crontab"].split()
            except ValueError:
                logger.error("crontab is not valid")
                return
            kwargs = dict(
                minute=minute, hour=hour, day_of_week=week,
                day_of_month=day, month_of_year=month, timezone=get_current_timezone()
            )
            crontab = CrontabSchedule.objects.filter(**kwargs).first()
            if crontab is None:
                crontab = CrontabSchedule.objects.create(**kwargs)
        else:
            logger.error("Schedule is not valid")
            return

        defaults = dict(
            interval=interval,
            crontab=crontab,
            name=name,
            task=detail['task'],
            args=json.dumps(detail.get('args', [])),
            kwargs=json.dumps(detail.get('kwargs', {})),
            description=detail.get('description') or ''
        )
        print(defaults)

        task = PeriodicTask.objects.update_or_create(
            defaults=defaults, name=name,
        )
        PeriodicTasks.update_changed()
        return task


def disable_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(name=task_name).update(enabled=False)
    PeriodicTasks.update_changed()


def delete_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(name=task_name).delete()
    PeriodicTasks.update_changed()


def get_celery_task_log_path(task_id):
    task_id = str(task_id)
    rel_path = os.path.join(task_id[0], task_id[1], task_id + '.log')
    path = os.path.join(settings.CELERY_LOG_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

