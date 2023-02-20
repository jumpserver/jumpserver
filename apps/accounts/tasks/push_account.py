from celery import shared_task
from django.utils.translation import gettext_noop, ugettext_lazy as _

from accounts.const import AutomationTypes
from accounts.tasks.common import automation_execute_start
from common.utils import get_logger

logger = get_logger(__file__)
__all__ = [
    'push_accounts_to_assets_task',
]


def push_util(account, asset_ids, task_name):
    task_snapshot = {
        'secret': account.secret,
        'secret_type': account.secret_type,
        'accounts': [account.username],
        'assets': asset_ids,
    }
    tp = AutomationTypes.push_account
    automation_execute_start(task_name, tp, task_snapshot)


@shared_task(
    queue="ansible", verbose_name=_('Push accounts to assets'),
    activity_callback=lambda self, account_ids, asset_ids: (account_ids, None)
)
def push_accounts_to_assets_task(account_ids, asset_ids):
    from accounts.models import PushAccountAutomation
    from assets.models import Asset
    from accounts.models import Account

    assets = Asset.objects.filter(id__in=asset_ids)
    accounts = Account.objects.filter(id__in=account_ids)

    task_name = gettext_noop("Push accounts to assets")
    task_name = PushAccountAutomation.generate_unique_name(task_name)

    for account in accounts:
        push_util(account, assets, task_name)
