# ~*~ coding: utf-8 ~*~
import json
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule


from common.utils import get_logger, get_object_or_none
from .models import Task, AdHoc

logger = get_logger(__file__)


def get_task_by_id(task_id):
    return get_object_or_none(Task, id=task_id)


def create_or_update_ansible_task(
        task_name, hosts, tasks, pattern='all', options=None,
        run_as_admin=False, run_as="", become_info=None,
        created_by=None, interval=None, crontab=None,
        is_periodic=False, callback=None,
    ):

    task = get_object_or_none(Task, name=task_name)

    if task is None:
        task = Task(
            name=task_name, interval=interval,
            crontab=crontab, is_periodic=is_periodic,
            callback=callback, created_by=created_by
        )
        task.save()

    adhoc = task.latest_adhoc
    new_adhoc = AdHoc(task=task, pattern=pattern,
                      run_as_admin=run_as_admin,
                      run_as=run_as)
    new_adhoc.hosts = hosts
    new_adhoc.tasks = tasks
    new_adhoc.options = options
    new_adhoc.become = become_info
    if not adhoc or adhoc != new_adhoc:
        new_adhoc.save()
        task.latest_adhoc = new_adhoc
    return task


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
        if isinstance(detail.get("interval"), int):
            interval, _ = IntervalSchedule.objects.get_or_create(
                every=detail['interval'],
                period=IntervalSchedule.SECONDS,
            )
        elif isinstance(detail.get("crontab"), str):
            try:
                minute, hour, day, month, week = detail["crontab"].split()
            except ValueError:
                raise SyntaxError("crontab is not valid")

            crontab, _ = CrontabSchedule.objects.get_or_create(
                minute=minute, hour=hour, day_of_week=week,
                day_of_month=day, month_of_year=month,
            )
        else:
            raise SyntaxError("Schedule is not valid")

        defaults = dict(
            interval=interval,
            crontab=crontab,
            name=name,
            task=detail['task'],
            args=json.dumps(detail.get('args', [])),
            kwargs=json.dumps(detail.get('kwargs', {})),
            enabled=detail['enabled']
        )

        task = PeriodicTask.objects.update_or_create(
            defaults=defaults, name=name,
        )
        logger.info("Create periodic task: {}".format(task))
        return task


def disable_celery_periodic_task(task_name):
    PeriodicTask.objects.filter(name=task_name).update(enabled=False)


def delete_celery_periodic_task(task_name):
    PeriodicTask.objects.filter(name=task_name).delete()


