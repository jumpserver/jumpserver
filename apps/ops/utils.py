# ~*~ coding: utf-8 ~*~
from django.utils.translation import ugettext_lazy as _
from common.utils import get_logger, get_object_or_none
from orgs.utils import set_to_root_org
from .models import Task, AdHoc

logger = get_logger(__file__)


def get_task_by_id(task_id):
    return get_object_or_none(Task, id=task_id)


def update_or_create_ansible_task(
        task_name, hosts, tasks, created_by,
        interval=None, crontab=None, is_periodic=False,
        callback=None, pattern='all', options=None,
        run_as_admin=False, run_as=None, become_info=None,
    ):
    if not hosts or not tasks or not task_name:
        return
    set_to_root_org()
    defaults = {
        'name': task_name,
        'interval': interval,
        'crontab': crontab,
        'is_periodic': is_periodic,
        'callback': callback,
        'created_by': created_by,
    }

    created = False
    task, ok = Task.objects.update_or_create(
        defaults=defaults, name=task_name, created_by=created_by
    )
    adhoc = task.get_latest_adhoc()
    new_adhoc = AdHoc(task=task, pattern=pattern,
                      run_as_admin=run_as_admin,
                      run_as=run_as)
    new_adhoc.tasks = tasks
    new_adhoc.options = options
    new_adhoc.become = become_info

    hosts_same = True
    if adhoc:
        old_hosts = set([str(asset.id) for asset in adhoc.hosts.all()])
        new_hosts = set([str(asset.id) for asset in hosts])
        hosts_same = old_hosts == new_hosts

    if not adhoc or adhoc != new_adhoc or not hosts_same:
        logger.debug(_("Update task content: {}").format(task_name))
        new_adhoc.save()
        new_adhoc.hosts.set(hosts)
        task.latest_adhoc = new_adhoc
        created = True
    return task, created



