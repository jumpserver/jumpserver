from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from accounts.const import AutomationTypes
from accounts.tasks.common import quickstart_automation_by_snapshot
from common.utils import get_logger

logger = get_logger(__file__)

__all__ = ['remove_accounts_task']


@shared_task(
    queue="ansible", verbose_name=_('Remove account'),
    activity_callback=lambda self, gather_account_ids, *args, **kwargs: (gather_account_ids, None)
)
def remove_accounts_task(gather_account_ids):
    from accounts.models import GatheredAccount

    gather_accounts = GatheredAccount.objects.filter(
        id__in=gather_account_ids
    )
    task_name = gettext_noop("Remove account")

    task_snapshot = {
        'assets': [str(i.asset_id) for i in gather_accounts],
        'gather_accounts': [str(i.id) for i in gather_accounts],
    }

    tp = AutomationTypes.remove_account
    quickstart_automation_by_snapshot(task_name, tp, task_snapshot)
