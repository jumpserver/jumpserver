# ~*~ coding: utf-8 ~*~

from collections import defaultdict
from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import get_logger
from orgs.utils import org_aware_func
from . import const
from .utils import check_asset_can_run_ansible


logger = get_logger(__file__)


__all__ = [
    'test_asset_user_connectivity_util', 'test_asset_users_connectivity_manual',
    'get_test_asset_user_connectivity_tasks',
]


def get_test_asset_user_connectivity_tasks(asset):
    if asset.is_unixlike():
        tasks = const.PING_UNIXLIKE_TASKS
    elif asset.is_windows():
        tasks = const.PING_WINDOWS_TASKS
    else:
        msg = _(
            "The asset {} system platform {} does not "
            "support run Ansible tasks".format(asset.hostname, asset.platform)
        )
        logger.info(msg)
        tasks = []
    return tasks


@org_aware_func("asset_user")
def test_asset_user_connectivity_util(asset_user, task_name, run_as_admin=False):
    """
    :param asset_user: <AuthBook>对象
    :param task_name:
    :param run_as_admin:
    :return:
    """
    from ops.utils import update_or_create_ansible_task

    if not check_asset_can_run_ansible(asset_user.asset):
        return

    tasks = get_test_asset_user_connectivity_tasks(asset_user.asset)
    if not tasks:
        logger.debug("No tasks ")
        return

    args = (task_name,)
    kwargs = {
        'hosts': [asset_user.asset], 'tasks': tasks,
        'options': const.TASK_OPTIONS,
    }
    if run_as_admin:
        kwargs["run_as_admin"] = True
    else:
        kwargs["run_as"] = asset_user.username
    task, created = update_or_create_ansible_task(*args, **kwargs)
    raw, summary = task.run()
    asset_user.set_connectivity(summary)


@shared_task(queue="ansible")
def test_asset_users_connectivity_manual(asset_users, run_as_admin=False):
    """
    :param asset_users: <AuthBook>对象
    """
    for asset_user in asset_users:
        task_name = _("Test asset user connectivity: {}").format(asset_user)
        test_asset_user_connectivity_util(asset_user, task_name, run_as_admin=run_as_admin)

#
# @shared_task(queue="ansible")
# def test_asset_user_connectivity_manual(asset_user):
#     """
#     :param asset_users: <AuthBook>对象
#     """
#     from .push_system_user import push_system_user_to_assets
#     system_users_assets_map = defaultdict(list)
#     for asset_user in asset_users:
#         if asset_user.prefer != "system_user":
#             continue


