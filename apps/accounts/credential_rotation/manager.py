from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from accounts.const import ChangeSecretRecordStatusChoice
from accounts.models import (
    ChangeSecretRecord, CredentialClientStatus, CredentialPolicy,
)


class CredentialRotationManager:
    def __init__(self, policy_id):
        self.policy_id = policy_id

    def _get_locked_policy(self):
        return CredentialPolicy.objects.select_for_update().select_related(
            'primary_account', 'backup_account', 'published_account'
        ).get(pk=self.policy_id)

    def start(self):
        policy = self._get_locked_policy()
        if policy.status != CredentialPolicy.Status.idle:
            raise ValidationError(
                _('The credential policy is already rotating.')
            )

        states = list(
            CredentialClientStatus.objects.select_for_update().filter(
                binding__policy=policy,
                client__is_active=True,
                client__type=F('binding__application__credential_access_mode'),
            )
        )
        if not states:
            raise ValidationError(_(
                'No active application client uses this credential policy.'
            ))

        policy.revision += 1
        policy.published_account = policy.backup_account
        policy.primary_version_at_start = policy.primary_account.version
        policy.status = CredentialPolicy.Status.waiting_backup
        policy.rotation_cancelled = False
        policy.date_rotation_started = timezone.now()
        policy.save(update_fields=[
            'revision', 'published_account', 'primary_version_at_start',
            'status', 'rotation_cancelled', 'date_rotation_started',
            'date_updated',
        ])
        state_ids = [state.id for state in states]
        CredentialClientStatus.objects.filter(id__in=state_ids).update(
            required_revision=policy.revision, is_rotation_participant=True,
        )
        return policy

    def check_usage(self):
        policy = self._get_locked_policy()
        if policy.status != CredentialPolicy.Status.waiting_backup:
            raise ValidationError(_(
                'The credential policy is not waiting for the backup account.'
            ))
        blockers = policy.get_blockers()
        if blockers:
            return policy, blockers
        policy.status = CredentialPolicy.Status.ready_for_change
        policy.save(update_fields=['status', 'date_updated'])
        return policy, []

    def check_secret_change(self):
        policy = self._get_locked_policy()
        if policy.status != CredentialPolicy.Status.ready_for_change:
            raise ValidationError(_(
                'The credential policy is not ready for secret change.'
            ))

        primary = policy.primary_account
        primary.refresh_from_db()
        record = ChangeSecretRecord.objects.filter(
            account=primary,
            account_version=policy.primary_version_at_start,
            status=ChangeSecretRecordStatusChoice.success,
            date_finished__gte=policy.date_rotation_started,
        ).order_by('-date_finished').first()
        changed = (
            primary.version > policy.primary_version_at_start
            and primary.change_secret_status == ChangeSecretRecordStatusChoice.success
            and record is not None
        )
        if not changed:
            raise ValidationError(_(
                'The primary account secret has not been changed '
                'and verified successfully.'
            ))

        policy.revision += 1
        policy.published_account = primary
        policy.status = CredentialPolicy.Status.waiting_primary
        policy.save(update_fields=[
            'revision', 'published_account', 'status', 'date_updated',
        ])
        CredentialClientStatus.objects.filter(
            binding__policy=policy, is_rotation_participant=True
        ).update(required_revision=policy.revision)
        return policy

    def complete(self):
        policy = self._get_locked_policy()
        if policy.status != CredentialPolicy.Status.waiting_primary:
            raise ValidationError(_(
                'The credential policy is not waiting for the primary account.'
            ))
        blockers = policy.get_blockers()
        if blockers:
            return policy, blockers

        if not policy.rotation_cancelled:
            policy.date_last_rotated = timezone.now()
        policy.status = CredentialPolicy.Status.idle
        policy.primary_version_at_start = None
        policy.date_rotation_started = None
        policy.rotation_cancelled = False
        policy.save(update_fields=[
            'status', 'date_last_rotated', 'primary_version_at_start',
            'date_rotation_started', 'rotation_cancelled', 'date_updated',
        ])
        CredentialClientStatus.objects.filter(
            binding__policy=policy, is_rotation_participant=True
        ).update(required_revision=None, is_rotation_participant=False)
        return policy, []

    def cancel(self):
        policy = self._get_locked_policy()
        if policy.status not in (
            CredentialPolicy.Status.waiting_backup,
            CredentialPolicy.Status.ready_for_change,
        ):
            raise ValidationError(_('This credential rotation cannot be cancelled.'))
        policy.revision += 1
        policy.published_account = policy.primary_account
        policy.status = CredentialPolicy.Status.waiting_primary
        policy.rotation_cancelled = True
        policy.save(update_fields=[
            'revision', 'published_account', 'status',
            'rotation_cancelled', 'date_updated',
        ])
        CredentialClientStatus.objects.filter(
            binding__policy=policy, is_rotation_participant=True
        ).update(required_revision=policy.revision)
        return policy
