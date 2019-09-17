# ~*~ coding: utf-8 ~*~

from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import get_logger
from . import const
from .utils import check_asset_can_run_ansible


logger = get_logger(__file__)


__all__ = [
    'test_asset_user_connectivity_util', 'test_asset_users_connectivity_manual',
    'get_test_asset_user_connectivity_tasks',
]


def get_test_asset_user_connectivity_tasks(asset):
    if asset.is_unixlike():
        tasks = const.TEST_ASSET_USER_CONN_TASKS
    elif asset.is_windows():
        tasks = const.TEST_WINDOWS_ASSET_USER_CONN_TASKS
    else:
        msg = _(
            "The asset {} system platform {} does not "
            "support run Ansible tasks".format(asset.hostname, asset.platform)
        )
        logger.info(msg)
        tasks = []
    return tasks


@shared_task(queue="ansible")
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
        'pattern': 'all', 'options': const.TASK_OPTIONS,
        'created_by': asset_user.org_id,
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


