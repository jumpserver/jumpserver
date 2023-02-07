from celery import shared_task
from django.utils.translation import gettext_noop
from django.utils.translation import ugettext as _

from common.utils import get_logger
from assets.const import GATEWAY_NAME
from accounts.const import AutomationTypes
from accounts.tasks.common import automation_execute_start
from orgs.utils import org_aware_func

logger = get_logger(__name__)
__all__ = [
    'verify_accounts_connectivity'
]


def verify_connectivity_util(assets, tp, accounts, task_name, **kwargs):
    if not assets or not accounts:
        return
    account_usernames = list(accounts.values_list('username', flat=True))
    child_snapshot = {
        'accounts': account_usernames,
        'assets': [str(asset.id) for asset in assets],
    }
    automation_execute_start(task_name, tp, child_snapshot, **kwargs)


@org_aware_func("assets")
def verify_accounts_connectivity_util(accounts, assets, task_name, **kwargs):
    gateway_assets = assets.filter(platform__name=GATEWAY_NAME)
    verify_connectivity_util(
        gateway_assets, AutomationTypes.verify_gateway_account,
        accounts, task_name, **kwargs
    )

    non_gateway_assets = assets.exclude(platform__name=GATEWAY_NAME)
    verify_connectivity_util(
        non_gateway_assets, AutomationTypes.verify_account,
        accounts, task_name, **kwargs
    )


@shared_task(queue="ansible", verbose_name=_('Verify asset account availability'))
def verify_accounts_connectivity(account_ids, asset_ids, **kwargs):
    from assets.models import Asset
    from accounts.models import Account, VerifyAccountAutomation
    assets = Asset.objects.filter(id__in=asset_ids)
    accounts = Account.objects.filter(id__in=account_ids)
    task_name = gettext_noop("Verify accounts connectivity")
    task_name = VerifyAccountAutomation.generate_unique_name(task_name)
    return verify_accounts_connectivity_util(accounts, assets, task_name, **kwargs)
