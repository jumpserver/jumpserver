from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.const import ApplicationEvent, AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import enqueue
from accounts.models import (
    ApplicationCredential, CredentialApplicationBinding, CredentialClientInstance,
    CredentialClientStatus, CredentialRotationRecord,
)
from common.exceptions import JMSException


class CredentialRotationManager:
    def __init__(self, credential_id):
        self.credential_id = credential_id

    def _get_locked_credential(self):
        return ApplicationCredential.objects.select_for_update(of=('self',)).select_related(
            'account', 'alternate_account', 'active_account'
        ).get(pk=self.credential_id)

    @transaction.atomic
    def start(self, operator='', operator_id=None):
        from . import preflight

        credential = self._get_locked_credential()
        preflight.check(credential)
        with preflight.account_locks(credential):
            return preflight.start(credential, operator, operator_id)

    def _publish(self, credential, operator=''):
        from .participants import initialize

        clients = CredentialClientInstance.objects.filter(
            configuration__credentials=credential,
            configuration__is_active=True,
            application__credential_bindings__credential=credential,
            application__is_active=True,
            is_active=True,
        ).select_related('application').distinct()
        for client in clients:
            binding = CredentialApplicationBinding.objects.get(
                credential=credential, application=client.application,
            )
            CredentialClientStatus.objects.get_or_create(binding=binding, client=client)
        states = list(credential.rotation_statuses().select_for_update(of=('self',)))
        source = credential.active_account
        target = credential.target_account
        if not target:
            raise JMSException(_('The alternating account configuration is incomplete.'))

        rotation = CredentialRotationRecord.objects.create(
            credential=credential,
            source_account=source,
            target_account=target,
            change_account=source,
            change_account_version_at_start=source.version,
            created_by=operator,
        )
        credential.revision += 1
        credential.active_account = target
        credential.status = ApplicationCredential.Status.waiting_switch
        credential.change_execution = None
        credential.rotation_cancelled = False
        credential.date_rotation_started = timezone.now()
        credential.save(update_fields=[
            'revision', 'active_account', 'status', 'rotation_cancelled',
            'date_rotation_started', 'date_updated', 'change_execution',
        ])
        event = record(AuditEvent.ROTATION_STARTED, credential=credential, operator=operator)
        enqueue(event, ApplicationEvent.ROTATION_STARTED)
        waiting = record(
            AuditEvent.ROTATION_STEP, credential=credential, operator=operator,
            summary='Waiting for clients to apply the target account.',
        )
        enqueue(waiting, ApplicationEvent.ROTATION_WAITING)
        CredentialClientStatus.objects.filter(id__in=[state.id for state in states]).update(
            required_revision=credential.revision, is_rotation_participant=True,
        )
        initialize(rotation, states)
        return credential

    @transaction.atomic
    def check_usage(self):
        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.waiting_switch:
            raise JMSException(_('The credential policy is not waiting for the account switch.'))
        blockers = credential.get_blockers()
        if blockers:
            return credential, blockers
        credential.status = ApplicationCredential.Status.ready_for_change
        credential.save(update_fields=['status', 'date_updated'])
        return credential, []

    @transaction.atomic
    def change_secret(self):
        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.ready_for_change:
            raise JMSException(_('The credential policy is not ready for secret change.'))
        if credential.get_blockers():
            raise JMSException(
                detail=_('Wait for all enabled clients to apply the target account.'),
                code='credential_rotation_clients_not_ready',
            )
        return credential

    @transaction.atomic
    def check_secret_change(self):
        from .execution import outcome, reconcile

        credential = self._get_locked_credential()
        if credential.status == ApplicationCredential.Status.waiting_revert:
            return credential
        if credential.status == ApplicationCredential.Status.idle:
            rotation = credential.rotation_records.first()
            if rotation and rotation.status == 'success':
                return credential
        if credential.status not in (
            ApplicationCredential.Status.changing_secret,
            ApplicationCredential.Status.recovery_required,
            ApplicationCredential.Status.change_failed,
        ):
            raise JMSException(_('No secret change is running for this credential policy.'))
        if credential.change_execution_id:
            reconcile(credential.change_execution_id)
            credential.refresh_from_db()
        else:
            credential.status = ApplicationCredential.Status.recovery_required
            credential.save(update_fields=['status', 'date_updated'])
        rotation = credential.rotation_records.first()
        if (
            not rotation
            or rotation.change_execution_id != credential.change_execution_id
            or outcome(credential, credential.change_execution) != 'success'
        ):
            return credential
        event = record(
            AuditEvent.SECRET_CHANGE_COMPLETED, credential=credential,
            summary=f'Execution {credential.change_execution_id} completed.',
        )
        enqueue(event, ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED)
        return self._finish(credential, rotation, 'success')

    def _finish(self, credential, rotation, status):
        from .participants import finalize

        now = timezone.now()
        finalize(credential, rotation)
        rotation.status = status
        rotation.date_finished = now
        rotation.save(update_fields=['status', 'date_finished', 'date_updated'])
        credential.status = ApplicationCredential.Status.idle
        credential.date_last_rotated = now if status == 'success' else credential.date_last_rotated
        credential.date_rotation_started = None
        credential.rotation_cancelled = False
        credential.change_execution = None
        credential.save(update_fields=[
            'status', 'date_last_rotated', 'date_rotation_started',
            'rotation_cancelled', 'change_execution', 'date_updated',
        ])
        CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True,
        ).update(required_revision=None, is_rotation_participant=False)
        if status == 'success':
            event = record(AuditEvent.ROTATION_STEP, credential=credential, summary='Rotation completed.')
            enqueue(event, ApplicationEvent.ROTATION_COMPLETED)
        return credential

    @transaction.atomic
    def complete(self):
        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.waiting_revert:
            raise JMSException(_('The credential policy is not waiting for account reversion.'))
        blockers = credential.get_blockers()
        if blockers:
            return credential, blockers
        rotation = credential.rotation_records.first()
        return self._finish(credential, rotation, 'cancelled'), []

    @transaction.atomic
    def cancel(self, reason=''):
        from .execution import outcome

        credential = self._get_locked_credential()
        if credential.status == ApplicationCredential.Status.change_failed:
            if not reason.strip() or outcome(credential, credential.change_execution) != 'unchanged':
                raise JMSException(_('Verify that the secret is unchanged and provide a cancellation reason.'))
        if credential.status not in (
            ApplicationCredential.Status.waiting_switch,
            ApplicationCredential.Status.ready_for_change,
            ApplicationCredential.Status.change_failed,
        ):
            raise JMSException(_('This credential rotation cannot be cancelled.'))
        rotation = credential.rotation_records.first()
        credential.revision += 1
        credential.active_account = rotation.source_account
        credential.status = ApplicationCredential.Status.waiting_revert
        credential.rotation_cancelled = True
        event = record(AuditEvent.ROTATION_CANCELLED, credential=credential, summary=reason)
        credential.save(update_fields=[
            'revision', 'active_account', 'status', 'rotation_cancelled', 'date_updated',
        ])
        enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED)
        CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True,
        ).update(required_revision=credential.revision)
        return credential
