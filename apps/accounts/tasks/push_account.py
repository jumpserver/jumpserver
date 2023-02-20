from celery import shared_task
from collections import defaultdict
from django.utils.translation import gettext_noop, ugettext_lazy as _

from accounts.const import AutomationTypes
from accounts.tasks.common import quickstart_automation_by_snapshot
from common.utils import get_logger

logger = get_logger(__file__)
__all__ = [
    'push_accounts_to_assets_task',
]


@shared_task(
    queue="ansible", verbose_name=_('Push accounts to assets'),
    activity_callback=lambda self, account_ids, asset_ids: (account_ids, None)
)
def push_accounts_to_assets_task(account_ids):
    from accounts.models import PushAccountAutomation
    from accounts.models import Account

    accounts = Account.objects.filter(id__in=account_ids)

    task_name = gettext_noop("Push accounts to assets")
    task_name = PushAccountAutomation.generate_unique_name(task_name)

    account_asset_mapper = defaultdict(set)
    for account in accounts:
        account_asset_mapper[account.username].add(account.asset)

    for username, assets in account_asset_mapper.items():
        task_snapshot = {
            'secret': account.secret,
            'secret_type': account.secret_type,
            'accounts': [account.username],
            'assets': asset_ids,
        }
        tp = AutomationTypes.push_account
        quickstart_automation_by_snapshot(task_name, tp, task_snapshot)