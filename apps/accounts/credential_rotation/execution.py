"""Bind existing account automation to one PAM rotation, without extending its tables."""
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from common.exceptions import JMSException

from accounts.const import AuditEvent, ChangeSecretRecordStatusChoice
from accounts.credential_client.audit import record as audit
from accounts.models import (
    Account, ApplicationCredential, AutomationExecution, ChangeSecretAutomation,
    ChangeSecretRecord, CredentialRotationRecord,
)
from common.const import Status
from common.const.choices import Trigger


def locked_rotation(rotation_id):
    rotation = CredentialRotationRecord.objects.get(pk=rotation_id)
    credential = ApplicationCredential.objects.select_for_update(of=('self',)).get(
        pk=rotation.credential_id,
    )
    rotation = CredentialRotationRecord.objects.select_for_update(of=('self',)).get(pk=rotation_id)
    if (
        not credential.is_active or credential.status == credential.Status.idle
        or rotation.date_finished or rotation.status != 'running'
        or credential.rotation_records.order_by('-date_created').first().id != rotation.id
    ):
        raise JMSException(_('This rotation is no longer active.'))
    return credential, rotation


def validate_parameters(credential, attrs, instance=None):
    def value(name, default=None):
        if name in attrs:
            return attrs[name]
        result = getattr(instance, name, default)
        return result.all() if hasattr(result, 'all') else result

    primary = credential.primary_account
    if (
        {str(asset.pk) for asset in value('assets', [])} != {str(primary.asset_id)}
        or list(value('nodes', []))
        or value('accounts', []) != [primary.username]
        or value('secret_type') != primary.secret_type
        or value('is_periodic', False)
        or not value('check_conn_after_change', True)
    ):
        raise JMSException(_(
            'A rotation task must target only its primary account, run once, '
            'and verify the secret after changing it.'
        ))


def dispatch(execution_id, org_id):
    from accounts.tasks.common import execute_credential_change
    from common.utils import get_logger
    try:
        execute_credential_change.apply_async(
            args=[str(execution_id), org_id], task_id=str(execution_id),
        )
    except Exception:
        # The broker may have accepted the message before the response was lost.
        # Keep the same pending execution; the worker claims it atomically.
        get_logger(__name__).exception('Dispatch rotation execution failed: %s', execution_id)


@transaction.atomic
def execute(rotation_id, operator='', previous_execution_id=None, reason=''):
    credential, rotation = locked_rotation(rotation_id)
    existing = rotation.change_execution
    if existing:
        if previous_execution_id is None or str(existing.id) != str(previous_execution_id):
            if existing.status == Status.pending:
                transaction.on_commit(lambda: dispatch(existing.id, credential.org_id))
            return existing
        reconcile(existing.id)
        credential.refresh_from_db()
        if credential.status != credential.Status.change_failed or not reason.strip():
            raise JMSException(_('Only a confirmed unchanged secret can be retried; provide a reason.'))
    elif credential.status != credential.Status.ready_for_change:
        raise JMSException(_('The application credential is not ready for secret change.'))

    if credential.rotation_mode == credential.RotationMode.dual and credential.get_blockers():
        raise JMSException(
            detail=_('Wait for all enabled clients to apply the backup account.'),
            code='credential_rotation_clients_not_ready',
        )
    automation = ChangeSecretAutomation.objects.filter(pk=rotation.change_automation_id).first()
    if not automation:
        raise JMSException(_('Save a change secret task for this rotation before executing it.'))
    if automation.org_id != credential.org_id or not automation.is_active:
        raise JMSException(_('The rotation task is inactive or belongs to another organization.'))
    validate_parameters(credential, {}, automation)
    primary = Account.objects.select_for_update().get(pk=credential.primary_account_id)
    if primary.version != credential.primary_version_at_start:
        raise JMSException(_('The account version changed outside this rotation; verification is required.'))
    snapshot = automation.to_attr_json()
    snapshot.update(
        accounts=[str(primary.id)],
        credential_rotation_id=str(rotation.id),
        application_credential_id=str(credential.id),
        expected_account_version=primary.version,
    )
    execution = AutomationExecution.objects.create(
        automation=automation, type='change_secret', trigger=Trigger.manual, snapshot=snapshot,
    )
    rotation.change_execution = execution
    rotation.save(update_fields=['change_execution'])
    credential.change_execution = execution
    credential.status = credential.Status.changing_secret
    credential.save(update_fields=['change_execution', 'status', 'date_updated'])
    audit(AuditEvent.ROTATION_STEP, credential=credential, operator=operator,
          summary=f'Change execution {execution.id}. {reason.strip()}')
    transaction.on_commit(lambda: dispatch(execution.id, credential.org_id))
    return execution


def outcome(credential, execution):
    if not execution:
        return 'unverified'
    snapshot = execution.snapshot or {}
    if (execution.org_id != credential.org_id or execution.type != 'change_secret'
            or snapshot.get('application_credential_id') != str(credential.id)):
        return 'unverified'
    if execution.status in (Status.pending, Status.running):
        return 'running'
    record = ChangeSecretRecord.objects.filter(
        execution_id=execution.id, account_id=credential.primary_account_id,
    ).first()
    primary = Account.objects.get(pk=credential.primary_account_id)
    expected_version = snapshot.get('expected_account_version')
    if not isinstance(expected_version, int):
        return 'unverified'
    if record and record.date_finished and execution.date_finished and (
        (record.status == ChangeSecretRecordStatusChoice.success
         and record.verification_status in ('', ChangeSecretRecordStatusChoice.success))
        or record.verification_status == ChangeSecretRecordStatusChoice.success
    ) and (
        expected_version == record.account_version
        and primary.version == expected_version + 1
        and record.new_secret is not None and primary.secret == record.new_secret
    ):
        return 'success'
    # The engine persists a candidate record before any remote mutation.
    # No record plus an unchanged account is safe only for a known bound execution.
    if (not record and expected_version == primary.version and execution.date_finished
            and (execution.summary or {}).get('rotation_no_remote_change')):
        return 'unchanged'
    return 'unverified'


@transaction.atomic
def reconcile(execution_id):
    execution = AutomationExecution.objects.get(pk=execution_id)
    rotation_id = (execution.snapshot or {}).get('credential_rotation_id')
    if not rotation_id:
        return
    try:
        credential, rotation = locked_rotation(rotation_id)
    except (CredentialRotationRecord.DoesNotExist, JMSException):
        return
    if (
        rotation.change_execution_id != execution.id
        or credential.change_execution_id != execution.id
        or credential.status not in (
            credential.Status.changing_secret, credential.Status.recovery_required,
            credential.Status.change_failed,
        )
    ):
        return
    result = outcome(credential, execution)
    status = {
        'unchanged': credential.Status.change_failed,
        'unverified': credential.Status.recovery_required,
    }.get(result)
    if status and credential.status != status:
        credential.status = status
        credential.save(update_fields=['status', 'date_updated'])
        audit(AuditEvent.SECRET_CHANGE_FINISHED, credential=credential,
              result='failed', summary=f'Execution {execution.id}: {result}')


def execution_info(credential):
    rotation = credential.rotation_records.select_related('change_execution').first()
    if not rotation or credential.status == credential.Status.idle:
        return None
    execution = rotation.change_execution
    info = {
        'id': str(rotation.id),
        'automation_id': str(rotation.change_automation_id) if rotation.change_automation_id else None,
        'execution_id': str(execution.id) if execution else None,
        'execution_status': execution.status if execution else None,
        'date_start': execution.date_start if execution else None,
        'outcome': outcome(credential, execution) if execution else None,
        'record_id': None, 'error': '',
    }
    if execution:
        record = ChangeSecretRecord.objects.filter(
            execution=execution, account_id=credential.primary_account_id,
        ).first()
        if record:
            info.update(record_id=str(record.id), error=record.verification_error or record.error or '')
        elif info['outcome'] == 'unverified':
            info['error'] = str(_('The execution result requires verification.'))
    return info
