from celery import shared_task
from django.utils.translation import gettext_noop
from django.utils.translation import ugettext as _

from common.utils import get_logger
from orgs.utils import org_aware_func, tmp_to_root_org

logger = get_logger(__name__)
__all__ = [
    'verify_accounts_connectivity'
]


@org_aware_func("assets")
def verify_accounts_connectivity_util(accounts, assets, task_name):
    from assets.models import VerifyAccountAutomation
    task_name = VerifyAccountAutomation.generate_unique_name(task_name)
    account_usernames = list(accounts.values_list('username', flat=True))

    data = {
        'name': task_name,
        'accounts': account_usernames,
        'comment': ', '.join([str(i) for i in assets])
    }
    instance = VerifyAccountAutomation.objects.create(**data)
    instance.assets.add(*assets)
    instance.execute()


@shared_task(queue="ansible", verbose_name=_('Verify asset account availability'))
def verify_accounts_connectivity(account_ids, asset_ids):
    from assets.models import Asset, Account
    with tmp_to_root_org():
        assets = Asset.objects.filter(id__in=asset_ids)
        accounts = Account.objects.filter(id__in=account_ids)

    task_name = gettext_noop("Verify accounts connectivity")
    return verify_accounts_connectivity_util(accounts, assets, task_name)
