from celery import shared_task
from django.utils.translation import gettext_noop, ugettext_lazy as _

from accounts.const import AutomationTypes
from accounts.tasks.common import automation_execute_start
from common.utils import get_logger
from orgs.utils import org_aware_func

logger = get_logger(__file__)
__all__ = [
    'push_accounts_to_assets',
]


def push_util(account, assets, task_name):
    task_snapshot = {
        'secret': account.secret,
        'secret_type': account.secret_type,
        'accounts': [account.username],
        'assets': [str(asset.id) for asset in assets],
    }
    tp = AutomationTypes.push_account
    automation_execute_start(task_name, tp, task_snapshot)


@org_aware_func("assets")
def push_accounts_to_assets_util(accounts, assets):
    from accounts.models import PushAccountAutomation

    task_name = gettext_noop("Push accounts to assets")
    task_name = PushAccountAutomation.generate_unique_name(task_name)
    for account in accounts:
        push_util(account, assets, task_name)


@shared_task(queue="ansible", verbose_name=_('Push accounts to assets'))
def push_accounts_to_assets(account_ids, asset_ids):
    from assets.models import Asset
    from accounts.models import Account

    assets = Asset.objects.filter(id__in=asset_ids)
    accounts = Account.objects.filter(id__in=account_ids)
    return push_accounts_to_assets_util(accounts, assets)
