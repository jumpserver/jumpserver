# -*- coding: utf-8 -*-
#
import json
import os

from django.conf import settings
from django.utils.timezone import get_current_timezone
from django.db.utils import ProgrammingError, OperationalError
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule


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
            intervals = IntervalSchedule.objects.filter(
                every=detail["interval"], period=IntervalSchedule.SECONDS
            )
            if intervals:
                interval = intervals[0]
            else:
                interval = IntervalSchedule.objects.create(
                    every=detail['interval'],
                    period=IntervalSchedule.SECONDS,
                )
        elif isinstance(detail.get("crontab"), str):
            try:
                minute, hour, day, month, week = detail["crontab"].split()
            except ValueError:
                raise SyntaxError("crontab is not valid")
            kwargs = dict(
                minute=minute, hour=hour, day_of_week=week,
                day_of_month=day, month_of_year=month, timezone=get_current_timezone()
            )
            contabs = CrontabSchedule.objects.filter(
                **kwargs
            )
            if contabs:
                crontab = contabs[0]
            else:
                crontab = CrontabSchedule.objects.create(**kwargs)
        else:
            raise SyntaxError("Schedule is not valid")

        defaults = dict(
            interval=interval,
            crontab=crontab,
            name=name,
            task=detail['task'],
            args=json.dumps(detail.get('args', [])),
            kwargs=json.dumps(detail.get('kwargs', {})),
            enabled=detail.get('enabled', True),
        )

        task = PeriodicTask.objects.update_or_create(
            defaults=defaults, name=name,
        )
        return task


def disable_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(name=task_name).update(enabled=False)


def delete_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(name=task_name).delete()


def get_celery_task_log_path(task_id):
    task_id = str(task_id)
    rel_path = os.path.join(task_id[0], task_id[1], task_id + '.log')
    path = os.path.join(settings.CELERY_LOG_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

