# ~*~ coding: utf-8 ~*~
from common.utils import get_logger, get_object_or_none
from .models import Task, AdHoc

logger = get_logger(__file__)


def get_task_by_id(task_id):
    return get_object_or_none(Task, id=task_id)


def update_or_create_ansible_task(
        task_name, hosts, tasks,
        interval=None, crontab=None, is_periodic=False,
        callback=None, pattern='all', options=None,
        run_as_admin=False, run_as="", become_info=None,
        created_by=None,
    ):
    if not hosts or not tasks or not task_name:
        return

    defaults = {
        'name': task_name,
        'interval': interval,
        'crontab': crontab,
        'is_periodic': is_periodic,
        'callback': callback,
        'created_by': created_by,
    }

    created = False
    task, _ = Task.objects.update_or_create(
        defaults=defaults, name=task_name,
    )

    adhoc = task.latest_adhoc
    new_adhoc = AdHoc(task=task, pattern=pattern,
                      run_as_admin=run_as_admin,
                      run_as=run_as)
    new_adhoc.hosts = hosts
    new_adhoc.tasks = tasks
    new_adhoc.options = options
    new_adhoc.become = become_info

    if not adhoc or adhoc != new_adhoc:
        print("Task create new adhoc: {}".format(task_name))
        new_adhoc.save()
        task.latest_adhoc = new_adhoc
        created = True
    return task, created



