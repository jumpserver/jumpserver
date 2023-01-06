from celery import shared_task
from django.utils.translation import gettext_noop
from django.utils.translation import ugettext as _

from common.utils import get_logger
from accounts.tasks.common import automation_execute_start
from accounts.const import AutomationTypes
from orgs.utils import org_aware_func

logger = get_logger(__name__)
__all__ = [
    'verify_accounts_connectivity'
]


@org_aware_func("assets")
def verify_accounts_connectivity_util(accounts, assets, task_name):
    from accounts.models import VerifyAccountAutomation
    task_name = VerifyAccountAutomation.generate_unique_name(task_name)
    account_usernames = list(accounts.values_list('username', flat=True))

    child_snapshot = {
        'accounts': account_usernames,
        'assets': [str(asset.id) for asset in assets],
    }
    tp = AutomationTypes.verify_account
    automation_execute_start(task_name, tp, child_snapshot)


@shared_task(queue="ansible", verbose_name=_('Verify asset account availability'))
def verify_accounts_connectivity(account_ids, asset_ids):
    from assets.models import Asset
    from accounts.models import Account
    assets = Asset.objects.filter(id__in=asset_ids)
    accounts = Account.objects.filter(id__in=account_ids)
    task_name = gettext_noop("Verify accounts connectivity")
    return verify_accounts_connectivity_util(accounts, assets, task_name)
