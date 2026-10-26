from collections import defaultdict

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_noop, gettext_lazy as _

from accounts.const import AutomationTypes, ChangeSecretAccountStatus
from accounts.tasks.common import quickstart_automation_by_snapshot
from accounts.utils import account_secret_task_status
from common.const import Status
from perms.const import ActionChoices
from users.models import User
from common.utils import get_logger
from orgs.utils import tmp_to_org, tmp_to_root_org

logger = get_logger(__file__)
__all__ = [
    'push_accounts_to_assets_task', 'change_secret_accounts_to_assets_task', 'push_same_name_account_task'
]



@shared_task(queue='ansible', soft_time_limit=600, time_limit=660,
             verbose_name=_('Push same-name account on first connection'))
def push_same_name_account_task(execution_id):
    from perms.utils import PermAssetDetailUtil
    from accounts.provisioning import push_policy
    from accounts.models import AutomationExecution, PushSecretRecord
    with tmp_to_root_org():
        execution = AutomationExecution.objects.filter(id=execution_id).first()
    if not execution:
        return
    with tmp_to_org(execution.org_id):
        with transaction.atomic():
            # Claim once, including broker redeliveries and late queued tasks.
            claimed = AutomationExecution.objects.filter(
                id=execution_id, status=Status.pending, date_finished__isnull=True,
            ).update(status=Status.running, date_start=timezone.now())
            if not claimed:
                return
        try:
            record = PushSecretRecord.objects.select_related('account__asset').get(
                execution_id=execution_id, is_first_login=True,
            )
            context = execution.snapshot.get('first_login', {})
            user = User.objects.filter(id=context.get('user_id')).first()
            protocol = context.get('protocol')
            if not user or not user.is_valid or not record.account:
                raise ValueError('Provisioning user is unavailable')
            account = record.account
            asset = account.asset
            permitted = PermAssetDetailUtil(user, asset).validate_permission(
                account.alias, protocol,
            )
            if (not asset.is_active or not account.is_active
                    or account.username != user.username
                    or not permitted or not permitted.actions & ActionChoices.connect
                    or permitted.date_expired <= timezone.now()
                    or not push_policy(user, asset, permitted, context.get('remote_addr', ''))):
                raise ValueError('Provisioning permission is no longer valid')
            execution.start()
            execution.refresh_from_db()
            record.refresh_from_db()
            if execution.is_success and record.status != 'success':
                AutomationExecution.objects.filter(id=execution_id).update(
                    status=Status.failed, date_finished=timezone.now(),
                )
        except Exception:
            logger.exception('First-login account push failed: execution=%s', execution_id)
            AutomationExecution.objects.filter(
                id=execution_id, status__in=[Status.pending, Status.running],
            ).update(
                status=Status.failed, date_finished=timezone.now(),
            )
        finally:
            # Permission/inventory failures may occur before the manager has
            # loaded the pre-created record. Never leave it pending forever.
            PushSecretRecord.objects.filter(execution_id=execution_id, status='pending').update(
                status='failed', date_finished=timezone.now(), date_updated=timezone.now(),
            )


def _process_accounts(account_ids, automation_model, default_name, automation_type, snapshot=None):
    from accounts.models import Account
    accounts = Account.objects.filter(id__in=account_ids)
    if not accounts:
        logger.warning(
            "No accounts found for automation task %s with ids %s",
            automation_type, account_ids
        )
        return

    task_name = automation_model.generate_unique_name(gettext_noop(default_name))
    snapshot = snapshot or {}
    snapshot.update({
        'accounts': [str(a.id) for a in accounts],
        'assets': [str(a.asset_id) for a in accounts],
    })

    quickstart_automation_by_snapshot(task_name, automation_type, snapshot)


@shared_task(
    queue="ansible",
    verbose_name=_('Push accounts to assets'),
    activity_callback=lambda self, account_ids, *args, **kwargs: (account_ids, None),
    description=_(
        "Whenever an account is created or modified and needs pushing to assets, run this task"
    )
)
def push_accounts_to_assets_task(account_ids, params=None):
    from accounts.models import PushAccountAutomation
    snapshot = {
        'params': params or {},
    }
    _process_accounts(
        account_ids,
        PushAccountAutomation,
        _("Push accounts to assets"),
        AutomationTypes.push_account,
        snapshot=snapshot
    )


@shared_task(
    queue="ansible",
    verbose_name=_('Change secret accounts to assets'),
    activity_callback=lambda self, account_ids, *args, **kwargs: (account_ids, None),
    description=_(
        "When a secret on an account changes and needs pushing to assets, run this task"
    )
)
def change_secret_accounts_to_assets_task(account_ids, params=None, snapshot=None, trigger='manual'):
    from accounts.models import ChangeSecretAutomation, Account

    manager = account_secret_task_status

    if trigger == 'delay':
        for _id in manager.account_ids:
            status = manager.get_status(_id)
            # Check if the account is in QUEUED status
            if status == ChangeSecretAccountStatus.QUEUED:
                account_ids.append(_id)
                manager.set_status(_id, ChangeSecretAccountStatus.READY)

    if not account_ids:
        return

    accounts = Account.objects.filter(id__in=account_ids)
    if not accounts:
        logger.warning(
            "No accounts found for change secret automation task with ids %s",
            account_ids
        )
        return

    grouped_ids = defaultdict(lambda: defaultdict(list))
    for account in accounts:
        grouped_ids[account.org_id][account.secret_type].append(str(account.id))

    snapshot = snapshot or {}
    for org_id, secret_map in grouped_ids.items():
        with tmp_to_org(org_id):
            for secret_type, ids in secret_map.items():
                snapshot['secret_type'] = secret_type
                _process_accounts(
                    ids,
                    ChangeSecretAutomation,
                    _("Change secret accounts to assets"),
                    AutomationTypes.change_secret,
                    snapshot=snapshot
                )
