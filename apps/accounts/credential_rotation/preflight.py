"""Backup verification using existing automation rows, snapshots and runners."""
from contextlib import ExitStack, contextmanager
from datetime import timedelta
from billiard.exceptions import SoftTimeLimitExceeded

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.const import AuditEvent
from accounts.credential_client.audit import record
from accounts.models import Account, ApplicationCredential, AutomationExecution, VerifyAccountAutomation
from common.const import Status
from common.exceptions import JMSException
from common.utils import get_logger

TIMEOUT = timedelta(minutes=10)
ERRORS = {
    'failed': _('Backup account verification failed. The primary account remains published.'),
    'timeout': _('Backup account verification timed out. Retry verification; rotation has not started.'),
    'changed': _('The account or credential changed during verification. Start verification again.'),
    'dispatch_failed': _('Unable to dispatch backup account verification. Please retry.'),
}


def check_ownership(credential, accounts):
    ids = [a.id for a in accounts if a]
    conflict = ApplicationCredential.objects.filter(
        Q(primary_account_id__in=ids) | Q(backup_account_id__in=ids),
    ).exclude(pk=credential.pk).first()
    if conflict:
        raise JMSException(code='credential_account_in_use', detail=_(
            'This account is already used by application credential "{name}". '
            'Choose another account or reuse that application credential.'
        ).format(name=conflict.name))


def check(credential):
    if not credential.is_active or credential.type != 'rotation' or credential.status != 'idle':
        raise JMSException(_('Only active, idle rotation credentials can start rotation.'))
    accounts = [credential.primary_account]
    if credential.rotation_mode == 'dual':
        accounts.append(credential.backup_account)
    if any(a is None for a in accounts):
        raise JMSException(_('The rotation account configuration is incomplete.'))
    if len(accounts) == 2 and (
        accounts[0].id == accounts[1].id
        or accounts[0].asset_id != accounts[1].asset_id
        or accounts[0].secret_type != accounts[1].secret_type
    ):
        raise JMSException(_('Primary and backup accounts must be different and use the same asset and secret type.'))
    check_ownership(credential, accounts)
    for account in accounts:
        if str(account.org_id) != str(credential.org_id) or str(account.asset.org_id) != str(credential.org_id):
            raise JMSException(_('The rotation accounts and asset must belong to the credential organization.'))
        if not account.is_active or not account.asset.is_active:
            raise JMSException(_('Account "{name}" or its asset is disabled.').format(name=account.name))
        if not account.has_secret:
            raise JMSException(_('Account "{name}" has no password or key.').format(name=account.name))


@contextmanager
def account_locks(credential):
    # The credential row is locked by the caller, as in the normal change engine.
    with ExitStack() as stack:
        for account_id in sorted(filter(None, (credential.primary_account_id, credential.backup_account_id))):
            lock = cache.lock(f'account-change-secret:{account_id}', expire=30, auto_renewal=True)
            if not lock.acquire(blocking=False):
                raise JMSException(_('An account change is already running. Wait before starting rotation.'))
            stack.callback(lock.release)
        yield


def fingerprint(credential):
    accounts = [credential.primary_account, credential.backup_account]
    return {
        'credential_id': str(credential.id), 'revision': credential.revision,
        'credential_updated': credential.date_updated.isoformat(),
        'accounts': [
            [str(a.id), a.version, a.username, a.secret_type, str(a.asset_id),
             a.asset.address, str(a.asset.platform_id), a.asset.date_updated.isoformat()]
            for a in accounts if a
        ],
    }


def task_name(credential):
    return f'PAM backup verification {credential.id}'


def authorized(execution):
    user_id = execution.snapshot.get('operator_id')
    if not user_id:
        return True
    from users.models import User
    user = User.objects.filter(pk=user_id, is_active=True).first()
    return user and all(user.has_perm(p) for p in (
        'accounts.change_applicationcredential', 'accounts.verify_account',
    ))


def latest(credential):
    return AutomationExecution.objects.filter(
        automation__name=task_name(credential),
        automation__params__credential_precheck=str(credential.id),
    ).order_by('-date_created', '-id').first()


def info(credential):
    execution = latest(credential)
    if not execution or credential.status != 'idle':
        return None
    state = (execution.summary or {}).get('precheck_status', 'checking')
    code = (execution.summary or {}).get('precheck_error', '')
    rejected = execution.automation.params.get('precheck_rejected', {})
    if rejected.get('id') == str(execution.id):
        state, code = 'failed', rejected['code']
    if state == 'checking':
        if timezone.now() >= execution.date_created + TIMEOUT:
            state, code = 'failed', 'timeout'
        elif execution.status not in (Status.pending, Status.running, Status.success):
            state, code = 'failed', 'failed'
    detail = rejected.get('detail') if rejected.get('id') == str(execution.id) else None
    return {'execution_id': str(execution.id), 'status': state, 'code': code,
            'detail': str(detail or ERRORS.get(code, '')), 'date_created': execution.date_created}


def start(credential, operator='', operator_id=None):
    current = info(credential)
    if current and current['status'] == 'checking':
        return credential
    task, created = VerifyAccountAutomation.objects.get_or_create(
        name=task_name(credential), type='verify_account',
        defaults={'params': {'credential_precheck': str(credential.id)}, 'is_periodic': False},
    )
    if task.params.get('credential_precheck') != str(credential.id):
        raise JMSException(_('The verification task name is already in use.'))
    task = VerifyAccountAutomation.objects.select_for_update().get(pk=task.pk)
    account = credential.backup_account
    tp = 'verify_gateway_account' if account.asset.is_gateway else 'verify_account'
    execution = AutomationExecution.objects.create(
        automation=task, type=tp,
        snapshot={
            'name': task.name, 'type': tp, 'org_id': str(credential.org_id),
            'assets': [str(account.asset_id)], 'accounts': [str(account.id)], 'nodes': [],
            'pam_precheck': fingerprint(credential), 'operator': operator,
            'operator_id': str(operator_id) if operator_id else None,
        },
    )
    record(AuditEvent.ROTATION_STEP, credential=credential, operator=operator,
           summary=f'Backup verification queued: {execution.id}')
    transaction.on_commit(lambda: dispatch(execution.id, credential.org_id))
    return credential


def dispatch(execution_id, org_id):
    from accounts.tasks.common import execute_credential_precheck
    try:
        execute_credential_precheck.apply_async(args=[str(execution_id), str(org_id)], task_id=str(execution_id))
    except Exception:
        get_logger(__name__).exception('Precheck dispatch failed: %s', execution_id)
        # A broker may have accepted the message. Keep the outcome fail-closed.
        fail(execution_id, 'dispatch_failed')


def fail(execution_id, code, detail=None):
    with transaction.atomic():
        execution = AutomationExecution.objects.select_for_update().get(pk=execution_id)
        if execution.summary.get('precheck_status') in ('passed', 'failed'):
            return
        execution.summary.update(precheck_status='failed', precheck_error=code)
        execution.status = Status.failed
        execution.date_finished = timezone.now()
        execution.save(update_fields=['summary', 'status', 'date_finished'])
        task = VerifyAccountAutomation.objects.select_for_update().get(pk=execution.automation_id)
        if task.executions.order_by('-date_created', '-id').first().id == execution.id:
            # The verification runner owns summary/status and can overwrite them.
            # Persist rejection independently so a late runner cannot publish.
            task.params['precheck_rejected'] = {'id': str(execution.id), 'code': code, 'detail': str(detail or '')}
            task.save(update_fields=['params'])
        credential_id = execution.snapshot['pam_precheck']['credential_id']
        credential = ApplicationCredential.objects.filter(pk=credential_id).first()
        if credential:
            record(AuditEvent.ROTATION_STEP, credential=credential, result='failed',
                   summary=str(detail or ERRORS.get(code, ERRORS['failed'])))


@transaction.atomic
def finish(execution_id):
    from .manager import CredentialRotationManager
    initial = AutomationExecution.objects.get(pk=execution_id)
    expected = initial.snapshot['pam_precheck']
    credential = ApplicationCredential.objects.select_for_update(of=('self',)).filter(
        pk=expected['credential_id'],
    ).first()
    if not credential:
        return
    execution = AutomationExecution.objects.select_for_update().get(pk=execution_id)
    if execution.summary.get('precheck_status') in ('passed', 'failed'):
        return
    current = latest(credential)
    if not current or current.id != execution.id:
        return fail(execution.id, 'changed')
    if execution.automation.params.get('precheck_rejected', {}).get('id') == str(execution.id):
        return
    if timezone.now() >= execution.date_created + TIMEOUT:
        return fail(execution.id, 'timeout')
    summary = execution.summary or {}
    if (execution.status != Status.success or not execution.date_finished
            or summary.get('ok_assets') != 1 or summary.get('fail_assets', 0)
            or summary.get('error_assets', 0)):
        return fail(execution.id, 'failed')
    try:
        with transaction.atomic(), account_locks(credential):
            # Serialize local password edits with the final fingerprint check and publication.
            list(Account.objects.select_for_update().filter(
                id__in=[credential.primary_account_id, credential.backup_account_id],
            ).order_by('id'))
            credential.refresh_from_db()
            check(credential)
            if fingerprint(credential) != expected:
                return fail(execution.id, 'changed')
            if not authorized(execution):
                return fail(execution.id, 'changed')
            CredentialRotationManager(credential.id)._publish(credential, execution.snapshot.get('operator', ''))
            execution.summary.update(precheck_status='passed')
            execution.save(update_fields=['summary'])
    except JMSException as exc:
        fail(execution.id, 'changed', exc.detail)


def run(execution_id):
    with transaction.atomic():
        initial = AutomationExecution.objects.get(pk=execution_id)
        credential = ApplicationCredential.objects.select_for_update().filter(
            pk=initial.snapshot['pam_precheck']['credential_id'],
        ).first()
        execution = AutomationExecution.objects.select_for_update().get(pk=execution_id)
        if execution.status != Status.pending or execution.summary.get('precheck_status'):
            return
        if timezone.now() >= execution.date_created + TIMEOUT:
            return fail(execution.id, 'timeout')
        current = latest(credential) if credential else None
        if (not current or current.id != execution.id or not authorized(execution)
                or fingerprint(credential) != execution.snapshot['pam_precheck']):
            return fail(execution.id, 'changed')
        try:
            check(credential)
        except JMSException as exc:
            return fail(execution.id, 'changed', exc.detail)
        from celery import current_task
        request = getattr(current_task, 'request', None)
        execution.snapshot['celery_task_id'] = str(execution.id)
        if request and request.hostname:
            execution.snapshot['celery_worker_hostname'] = request.hostname
        execution.status = Status.running
        execution.save(update_fields=['status', 'snapshot'])
    try:
        execution.start()
        finish(execution.id)
    except SoftTimeLimitExceeded:
        fail(execution.id, 'timeout')
    except Exception:
        get_logger(__name__).exception('Backup verification failed: %s', execution.id)
        fail(execution.id, 'failed')
