from collections import defaultdict

from celery import shared_task
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext_noop

from accounts.const import AutomationTypes
from accounts.tasks.common import quickstart_automation_by_snapshot
from common.utils import get_logger
from orgs.utils import org_aware_func, tmp_to_org, tmp_to_root_org

logger = get_logger(__name__)
__all__ = [
    'verify_accounts_connectivity_task',
    'verify_change_secret_records_task',
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

    gateways = assets.gateways()
    verify_connectivity_util(
        gateways, AutomationTypes.verify_gateway_account,
        accounts, task_name
    )

    common_assets = assets.gateways(0)
    verify_connectivity_util(
        common_assets, AutomationTypes.verify_account,
        accounts, task_name
    )


@shared_task(
    queue="ansible",
    verbose_name=_('Verify asset account availability'),
    activity_callback=lambda self, account_ids, *args, **kwargs: (account_ids, None),
    description=_(
        "When clicking 'Test' in 'Console - Asset details - Accounts' this task will be executed"
    )
)
def verify_accounts_connectivity_task(account_ids):
    from accounts.models import Account, VerifyAccountAutomation
    accounts = Account.objects.filter(id__in=account_ids)
    task_name = gettext_noop("Verify accounts connectivity")
    task_name = VerifyAccountAutomation.generate_unique_name(task_name)
    return verify_accounts_connectivity_util(accounts, task_name)


def change_secret_record_activity_callback(
        self, record_ids, *args, **kwargs
):
    from accounts.models import ChangeSecretRecord

    with tmp_to_root_org():
        records = list(
            ChangeSecretRecord.objects.filter(
                id__in=record_ids,
                execution__isnull=False,
                asset__isnull=False,
            )
            .select_related('execution')
        )
    if not records:
        return
    resource_ids = [str(record.asset_id) for record in records]
    return resource_ids, records[0].execution.org_id


@shared_task(
    queue="ansible",
    verbose_name=_('Verify change secret records'),
    activity_callback=change_secret_record_activity_callback,
    description=_(
        "Verify the candidate credentials saved by change secret records"
    )
)
def verify_change_secret_records_task(record_ids):
    from accounts.const import ChangeSecretRecordStatusChoice
    from accounts.models import ChangeSecretRecord, VerifyAccountAutomation

    with tmp_to_root_org():
        records = list(
            ChangeSecretRecord.objects.filter(id__in=record_ids)
            .select_related('account', 'asset', 'execution')
            .order_by('-date_updated')
        )

    unique_records = {}
    for record in records:
        if not record.account_id or not record.asset_id or not record.execution:
            continue
        unique_records.setdefault(str(record.account_id), record)

    records_by_org = defaultdict(list)
    for record in unique_records.values():
        records_by_org[record.execution.org_id].append(record)

    for org_id, org_records in records_by_org.items():
        record_ids = [record.id for record in org_records]
        with tmp_to_root_org():
            ChangeSecretRecord.objects.filter(id__in=record_ids).update(
                verification_status=(
                    ChangeSecretRecordStatusChoice.pending.value
                ),
                verification_error='',
                date_verified=None,
            )

        record_map = {
            f'{record.asset_id}-{record.account_id}': str(record.id)
            for record in org_records
        }
        snapshot = {
            'accounts': [str(record.account_id) for record in org_records],
            'assets': [str(record.asset_id) for record in org_records],
            'recovery_record_map': record_map,
        }
        with tmp_to_org(org_id):
            task_name = VerifyAccountAutomation.generate_unique_name(
                gettext_noop('Verify change secret records')
            )
            quickstart_automation_by_snapshot(
                task_name, AutomationTypes.verify_account, snapshot
            )
