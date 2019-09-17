# ~*~ coding: utf-8 ~*~

from collections import defaultdict
from celery import shared_task
from django.utils.translation import ugettext as _

from . import const


@shared_task(queue="ansible")
def gather_asset_all_users(assets, task_name=None):
    from ops.utils import update_or_create_ansible_task
    if task_name is None:
        task_name = _("Gather assets users")
    hosts_category = {
        'linux': {
            'hosts': [],
            'tasks': const.GATHER_ASSET_USERS_TASKS
        },
        'windows': {
            'hosts': [],
            'tasks': const.GATHER_ASSET_USERS_TASKS_WINDOWS
        }
    }
    for asset in assets:
        hosts_list = hosts_category['windows']['hosts'] if asset.is_windows() \
            else hosts_category['linux']['hosts']
        hosts_list.append(asset)

    results = {'linux': defaultdict(dict), 'windows': defaultdict(dict)}
    for k, value in hosts_category.items():
        if not value['hosts']:
            continue
        task, created = update_or_create_ansible_task(
            task_name=task_name, hosts=value['hosts'], tasks=value['tasks'],
            pattern='all', options=const.TASK_OPTIONS,
            run_as_admin=True, created_by=value['hosts'][0].org_id,
        )
        raw, summary = task.run()
        results[k].update(raw['ok'])
    return results

