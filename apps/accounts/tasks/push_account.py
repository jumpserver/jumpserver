from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from accounts.const import AutomationTypes
from accounts.tasks.common import quickstart_automation_by_snapshot
from common.utils import get_logger

logger = get_logger(__file__)
__all__ = [
    'push_accounts_to_assets_task',
]


@shared_task(
    queue="ansible", verbose_name=_('Push accounts to assets'),
    activity_callback=lambda self, account_ids, *args, **kwargs: (account_ids, None)
)
def push_accounts_to_assets_task(account_ids, params=None):
    from accounts.models import PushAccountAutomation
    from accounts.models import Account

    accounts = Account.objects.filter(id__in=account_ids)
    task_name = gettext_noop("Push accounts to assets")
    task_name = PushAccountAutomation.generate_unique_name(task_name)

    task_snapshot = {
        'accounts': [str(account.id) for account in accounts],
        'assets': [str(account.asset_id) for account in accounts],
        'params': params or {},
    }

    tp = AutomationTypes.push_account
    quickstart_automation_by_snapshot(task_name, tp, task_snapshot)
