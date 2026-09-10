from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from common.exceptions import JMSException

from accounts.const import AuditEvent
from accounts.credential_client.audit import record
from accounts.models import (
    CredentialClientStatus, ApplicationCredential,
    CredentialRotationRecord,
)


class CredentialRotationManager:
    def __init__(self, credential_id):
        self.credential_id = credential_id

    def _get_locked_credential(self):
        return ApplicationCredential.objects.select_for_update(of=('self',)).select_related(
            'primary_account', 'backup_account', 'published_account'
        ).get(pk=self.credential_id)

    @transaction.atomic
    def start(self, operator='', operator_id=None):
        from . import preflight
        credential = self._get_locked_credential()
        preflight.check(credential)
        with preflight.account_locks(credential):
            if credential.rotation_mode == credential.RotationMode.dual:
                return preflight.start(credential, operator, operator_id)
            return self._publish(credential, operator)

    def _publish(self, credential, operator=''):
        states = list(credential.rotation_statuses().select_for_update(of=('self',)))
        dual = credential.rotation_mode == ApplicationCredential.RotationMode.dual
        if dual:
            credential.revision += 1
            credential.published_account = credential.backup_account
        credential.primary_version_at_start = credential.primary_account.version
        credential.status = (
            ApplicationCredential.Status.waiting_backup if dual
            else ApplicationCredential.Status.ready_for_change
        )
        credential.change_execution = None
        credential.rotation_cancelled = False
        credential.date_rotation_started = timezone.now()
        CredentialRotationRecord.objects.create(credential=credential, created_by=operator)
        record(AuditEvent.ROTATION_STARTED, credential=credential, operator=operator)
        credential.save(update_fields=[
            'revision', 'published_account', 'primary_version_at_start',
            'status', 'rotation_cancelled', 'date_rotation_started',
            'date_updated', 'change_execution',
        ])
        state_ids = [state.id for state in states]
        CredentialClientStatus.objects.filter(id__in=state_ids).update(
            required_revision=credential.revision, is_rotation_participant=True,
        )
        return credential

    def check_usage(self):
        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.waiting_backup:
            raise JMSException(_(
                'The application credential is not waiting for the backup account.'
            ))
        blockers = credential.get_blockers()
        if blockers:
            return credential, blockers
        credential.status = ApplicationCredential.Status.ready_for_change
        credential.save(update_fields=['status', 'date_updated'])
        return credential, []

    def change_secret(self):
        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.ready_for_change:
            raise JMSException(_(
                'The application credential is not ready for secret change.'
            ))
        if credential.rotation_mode == ApplicationCredential.RotationMode.dual and credential.get_blockers():
            raise JMSException(
                detail=_('Wait for all enabled clients to apply the backup account.'),
                code='credential_rotation_clients_not_ready',
            )
        return credential

    def check_secret_change(self):
        from .execution import outcome, reconcile
        credential = self._get_locked_credential()
        if credential.status == ApplicationCredential.Status.waiting_primary:
            return credential
        if credential.status not in (
            ApplicationCredential.Status.changing_secret,
            ApplicationCredential.Status.recovery_required,
            ApplicationCredential.Status.change_failed,
        ):
            raise JMSException(_('No secret change is running for this credential.'))
        if credential.change_execution_id:
            reconcile(credential.change_execution_id)
            credential.refresh_from_db()
        else:
            credential.status = ApplicationCredential.Status.recovery_required
            credential.save(update_fields=['status', 'date_updated'])
        rotation = credential.rotation_records.first()
        if (not rotation or rotation.change_execution_id != credential.change_execution_id
                or outcome(credential, credential.change_execution) != 'success'):
            # Return the persisted recovery state, rather than rolling it back
            # through ATOMIC_REQUESTS on a validation exception.
            return credential
        primary = credential.primary_account
        primary.refresh_from_db()
        credential.revision += 1
        credential.published_account = primary
        credential.status = ApplicationCredential.Status.waiting_primary
        credential.save(update_fields=[
            'revision', 'published_account', 'status', 'date_updated', 'change_execution',
        ])
        CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True
        ).update(required_revision=credential.revision)
        return credential

    def complete(self):
        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.waiting_primary:
            raise JMSException(_(
                'The application credential is not waiting for the primary account.'
            ))
        blockers = credential.get_blockers()
        if blockers:
            return credential, blockers

        if not credential.rotation_cancelled:
            credential.date_last_rotated = timezone.now()
        credential.rotation_records.filter(date_created__gte=credential.date_rotation_started).update(
            status='cancelled' if credential.rotation_cancelled else 'success',
            date_finished=timezone.now(),
        )
        credential.status = ApplicationCredential.Status.idle
        credential.primary_version_at_start = None
        credential.date_rotation_started = None
        credential.rotation_cancelled = False
        credential.save(update_fields=[
            'status', 'date_last_rotated', 'primary_version_at_start',
            'date_rotation_started', 'rotation_cancelled', 'date_updated',
        ])
        CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True
        ).update(required_revision=None, is_rotation_participant=False)
        return credential, []

    def cancel(self, reason=''):
        from .execution import outcome
        credential = self._get_locked_credential()
        if credential.status == ApplicationCredential.Status.change_failed:
            if not reason.strip() or outcome(credential, credential.change_execution) != 'unchanged':
                raise JMSException(_('Verify that the secret is unchanged and provide a cancellation reason.'))
        if credential.status not in (
            ApplicationCredential.Status.waiting_backup,
            ApplicationCredential.Status.ready_for_change,
            ApplicationCredential.Status.change_failed,
        ):
            raise JMSException(_('This credential rotation cannot be cancelled.'))
        credential.revision += 1
        credential.published_account = credential.primary_account
        credential.status = ApplicationCredential.Status.waiting_primary
        credential.rotation_cancelled = True
        record(AuditEvent.ROTATION_CANCELLED, credential=credential, summary=reason)
        credential.save(update_fields=[
            'revision', 'published_account', 'status',
            'rotation_cancelled', 'date_updated',
        ])
        CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True
        ).update(required_revision=credential.revision)
        return credential
