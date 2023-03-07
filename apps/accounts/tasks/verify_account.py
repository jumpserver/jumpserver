from celery import shared_task
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext_noop

from accounts.const import AutomationTypes
from accounts.tasks.common import quickstart_automation_by_snapshot
from assets.const import GATEWAY_NAME
from common.utils import get_logger
from orgs.utils import org_aware_func

logger = get_logger(__name__)
__all__ = [
    'verify_accounts_connectivity_task'
]


def verify_connectivity_util(assets, tp, accounts, task_name):
    if not assets or not accounts:
        return
    account_ids = [str(account.id) for account in accounts]
    task_snapshot = {
        'accounts': account_ids,
        'assets': [str(asset.id) for asset in assets],
    }
    quickstart_automation_by_snapshot(task_name, tp, task_snapshot)


@org_aware_func("assets")
def verify_accounts_connectivity_util(accounts, task_name):
    from assets.models import Asset

    asset_ids = [a.asset_id for a in accounts]
    assets = Asset.objects.filter(id__in=asset_ids)

    gateways = assets.filter(platform__name=GATEWAY_NAME)
    verify_connectivity_util(
        gateways, AutomationTypes.verify_gateway_account,
        accounts, task_name
    )

    common_assets = assets.exclude(platform__name=GATEWAY_NAME)
    verify_connectivity_util(
        common_assets, AutomationTypes.verify_account,
        accounts, task_name
    )


@shared_task(
    queue="ansible", verbose_name=_('Verify asset account availability'),
    activity_callback=lambda self, account_ids, *args, **kwargs: (account_ids, None)
)
def verify_accounts_connectivity_task(account_ids):
    from accounts.models import Account, VerifyAccountAutomation
    accounts = Account.objects.filter(id__in=account_ids)
    task_name = gettext_noop("Verify accounts connectivity")
    task_name = VerifyAccountAutomation.generate_unique_name(task_name)
    return verify_accounts_connectivity_util(accounts, task_name)
