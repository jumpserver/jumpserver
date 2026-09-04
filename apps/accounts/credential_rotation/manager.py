from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from accounts.const import ChangeSecretRecordStatusChoice
from accounts.models import (
    ChangeSecretRecord, CredentialClientStatus, ApplicationCredential,
    CredentialRotationRecord,
)


class CredentialRotationManager:
    def __init__(self, credential_id):
        self.credential_id = credential_id

    def _get_locked_credential(self):
        return ApplicationCredential.objects.select_for_update(of=('self',)).select_related(
            'primary_account', 'backup_account', 'published_account'
        ).get(pk=self.credential_id)

    def start(self, operator=''):
        credential = self._get_locked_credential()
        if credential.type == ApplicationCredential.Type.fixed or not credential.is_active:
            raise ValidationError(_('Only active rotation credentials can rotate.'))
        if credential.status != ApplicationCredential.Status.idle:
            raise ValidationError(
                _('The application credential is already rotating.')
            )

        states = list(
            CredentialClientStatus.objects.select_for_update().filter(
                binding__credential=credential,
                client__is_active=True,
                client__configuration__is_active=True,
                client__application__is_active=True,
            )
        )
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
        credential.save(update_fields=[
            'revision', 'published_account', 'primary_version_at_start',
            'status', 'rotation_cancelled', 'date_rotation_started',
            'date_updated', 'change_execution',
        ])
        state_ids = [state.id for state in states]
        CredentialClientStatus.objects.filter(id__in=state_ids).update(
            required_revision=credential.revision, is_rotation_participant=True,
        )
        CredentialRotationRecord.objects.create(credential=credential, created_by=operator)
        return credential

    def check_usage(self):
        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.waiting_backup:
            raise ValidationError(_(
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
            raise ValidationError(_(
                'The application credential is not ready for secret change.'
            ))
        if credential.rotation_mode == ApplicationCredential.RotationMode.dual and credential.get_blockers():
            raise ValidationError(_('Wait for all enabled clients to apply the backup account.'))
        credential.status = ApplicationCredential.Status.changing_secret
        credential.save(update_fields=['status', 'date_updated'])
        return credential

    def check_secret_change(self):
        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.changing_secret:
            raise ValidationError(_('No secret change is running for this credential.'))

        primary = credential.primary_account
        primary.refresh_from_db()
        record = ChangeSecretRecord.objects.filter(
            execution__org_id=credential.org_id,
            execution__type='change_secret',
            account=primary,
            account_version=primary.version - 1,
            status=ChangeSecretRecordStatusChoice.success,
            date_finished__gte=credential.date_rotation_started,
        ).order_by('-date_finished').first()
        changed = (
            primary.version > credential.primary_version_at_start
            and primary.change_secret_status == ChangeSecretRecordStatusChoice.success
            and record is not None
        )
        if not changed:
            raise ValidationError(_(
                'The primary account secret has not been changed '
                'and verified successfully.'
            ))

        credential.revision += 1
        credential.change_execution_id = record.execution_id
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
            raise ValidationError(_(
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

    def cancel(self):
        credential = self._get_locked_credential()
        if credential.status not in (
            ApplicationCredential.Status.waiting_backup,
            ApplicationCredential.Status.ready_for_change,
        ):
            raise ValidationError(_('This credential rotation cannot be cancelled.'))
        credential.revision += 1
        credential.published_account = credential.primary_account
        credential.status = ApplicationCredential.Status.waiting_primary
        credential.rotation_cancelled = True
        credential.save(update_fields=[
            'revision', 'published_account', 'status',
            'rotation_cancelled', 'date_updated',
        ])
        CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True
        ).update(required_revision=credential.revision)
        return credential
