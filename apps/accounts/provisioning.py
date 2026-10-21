from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.const import AliasAccount, AutomationTypes, SecretStrategy, SecretType
from accounts.models import Account, AutomationExecution, PushSecretRecord
from accounts.utils import SecretGenerator, validate_account_username
from assets.models import Asset
from assets.tasks.common import generate_automation_execution_data
from common.const import Status
from common.utils import get_logger
from orgs.utils import tmp_to_org
from perms.const import ActionChoices

logger = get_logger(__name__)


def auto_push_enabled(account, protocol):
    protocols = getattr(account, 'auto_push_protocols', ())
    return protocol in protocols or 'all' in protocols


def needs_account_preparation(account, protocol):
    if not auto_push_enabled(account, protocol):
        return False
    if account.is_virtual():
        return True
    record = get_preparation_record(account)
    return bool(record and get_preparation_status(record) != 'ready')


def get_preparation_record(account):
    return PushSecretRecord.objects.filter(
        account=account, is_first_login=True,
    ).select_related('execution').order_by('-date_created', '-id').first()


def get_preparation_status(record):
    execution = record.execution
    if not execution:
        return 'failed'
    if execution.is_finished:
        return 'ready' if execution.is_success and record.status == 'success' else 'failed'
    if execution.status == Status.pending:
        return 'queued'
    if execution.status == Status.running:
        return 'running'
    return 'failed'


def get_permitted_account(token):
    # @USER becomes a real account alias after the first account is created.
    alias = token.account
    if alias == AliasAccount.USER:
        account = token.asset.all_valid_accounts.filter(username=token.user.username).first()
        if account:
            alias = account.alias
    account = token.get_user_permed_account(token.user, token.asset, alias, token.protocol)
    if (not account or not account.actions & ActionChoices.connect
            or account.date_expired <= timezone.now()):
        raise PermissionDenied(_('Permission to connect to this account is no longer available.'))
    return account


def check_account_ready(token, account):
    """Component credential APIs must not bypass first-login preparation."""
    with tmp_to_org(token.asset.org_id):
        if account.is_virtual():
            if token.account == AliasAccount.USER and not token.personal_credential_id:
                permitted = get_permitted_account(token)
                if auto_push_enabled(permitted, token.protocol):
                    raise PermissionDenied(_('Prepare the same-name account before connecting.'))
            return
        record = get_preparation_record(account) if account.pk else None
        if record and get_preparation_status(record) != 'ready':
            raise PermissionDenied(_('Account preparation has not succeeded. Please retry.'))


def _response(record):
    status = get_preparation_status(record)
    messages = {
        'queued': _('Waiting to push the same-name account.'),
        'running': _('Creating the account and configuring its login credentials.'),
        'failed': _('Account preparation failed. Retry or contact an administrator with the task ID.'),
        'ready': _('Account is ready. Connecting.'),
    }
    return {
        'status': status,
        'detail': str(messages[status]),
        'execution_id': str(record.execution_id or ''),
    }


def _dispatch(execution_id):
    from accounts.tasks.push_account import push_same_name_account_task

    try:
        push_same_name_account_task.apply_async(
            args=(str(execution_id),), task_id=str(execution_id),
        )
    except Exception:
        logger.exception('Queue first-login account push failed: execution=%s', execution_id)
        failed = AutomationExecution.objects.filter(id=execution_id, status=Status.pending).update(
            status=Status.failed, date_finished=timezone.now(),
        )
        if failed:
            PushSecretRecord.objects.filter(execution_id=execution_id, status='pending').update(
                status='failed', date_finished=timezone.now(), date_updated=timezone.now(),
            )


def _start(account, user, protocol):
    record_id = uuid4()
    snapshot = {
        'accounts': [str(account.id)], 'assets': [str(account.asset_id)],
        'secret_type': account.secret_type, 'secret_strategy': SecretStrategy.custom,
        'check_conn_after_change': True, 'params': {},
        'first_login': {'user_id': str(user.id), 'protocol': protocol},
        'record_map': {f'{account.asset_id}-{account.id}': str(record_id)},
    }
    data = generate_automation_execution_data(
        str(_('First-login same-name account push')), AutomationTypes.push_account, snapshot,
    )
    execution = AutomationExecution.objects.create(type=AutomationTypes.push_account, **data)
    # Persist the account/execution association before enqueueing. The push
    # manager reuses this record even if inventory preparation fails early.
    record = PushSecretRecord.objects.create(
        id=record_id, account=account, asset=account.asset, execution=execution,
        is_first_login=True, created_by=user.username,
        comment=f'{account.username}@{account.asset.address}',
    )
    transaction.on_commit(lambda: _dispatch(execution.id))
    return record


def _cancel_stale_queued_record(record):
    execution = record.execution
    if (not execution or execution.status != Status.pending or execution.is_finished
            or execution.date_created >= timezone.now() - timedelta(minutes=5)):
        return record
    # The worker claims the same pending execution atomically. A late broker
    # delivery cannot start this execution once a retry has replaced it.
    canceled = AutomationExecution.objects.filter(
        id=execution.id, status=Status.pending, date_finished__isnull=True,
    ).update(status=Status.canceled, date_finished=timezone.now())
    if canceled:
        PushSecretRecord.objects.filter(id=record.id, status='pending').update(
            status='failed', date_finished=timezone.now(), date_updated=timezone.now(),
        )
    return PushSecretRecord.objects.select_related('execution').get(id=record.id)


@transaction.atomic
def prepare_account(token, *, retry=False):
    with tmp_to_org(token.asset.org_id):
        # Serialize creation/retries across tabs and users; never hold this lock
        # while the remote push is running.
        Asset.objects.select_for_update().get(id=token.asset_id)
        permitted = get_permitted_account(token)
        if (permitted.username != token.user.username
                or not auto_push_enabled(permitted, token.protocol)):
            raise PermissionDenied(_('Automatic same-name account push is not authorized.'))

        account = permitted if not permitted.is_virtual() else (
            token.asset.all_accounts.filter(username=token.user.username).order_by(
                '-is_active', 'secret_type', 'id',
            ).first()
        )
        if account:
            # Joined-directory accounts may be shared by multiple assets.
            # Their retries must also serialize on the account itself.
            account = Account.objects.select_for_update().get(id=account.id)
        if account and not account.is_active:
            raise ValidationError(_('The existing same-name account is inactive. Contact an administrator.'))
        if account is None:
            username = validate_account_username(token.user.username)
            if (not username or username != token.user.username or username.startswith('@')
                    or username.casefold() in {
                'root', 'administrator',
            }):
                raise ValidationError(_('This username cannot be provisioned automatically.'))
            automation = getattr(token.asset.platform, 'automation', None)
            if not (automation and automation.ansible_enabled and automation.push_account_enabled
                    and automation.push_account_method):
                raise ValidationError(_('Account push is not enabled for this asset platform.'))
            account = Account.objects.create(
                asset=token.asset, name=username, username=username,
                secret_type=SecretType.PASSWORD,
                secret=SecretGenerator(SecretStrategy.random, SecretType.PASSWORD).get_secret(),
                privileged=False, created_by=token.user.username,
            )
            record = _start(account, token.user, token.protocol)
        else:
            record = get_preparation_record(account)
            if record:
                record = _cancel_stale_queued_record(record)
                if retry and get_preparation_status(record) == 'failed':
                    record = _start(account, token.user, token.protocol)

        if record and get_preparation_status(record) != 'ready':
            return _response(record)

        # Bind the previously virtual token to the managed account and its
        # verified credentials. Existing accounts are reused without a push.
        token.account = account.alias
        if account.has_secret:
            token.input_secret = ''
            token.input_secret_type = account.secret_type
        token.renewal()
        return {'status': 'ready', 'detail': str(_('Account is ready. Connecting.'))}
