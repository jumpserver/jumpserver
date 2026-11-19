from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.const import ApplicationEvent, AuditEvent, AuditSource
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

    def _publish(self, credential, operator='', rotation_id=None, operator_id=None):
        from .participants import initialize
        from accounts.credential_client.manager import client_uses_credential

        clients = CredentialClientInstance.objects.filter(
            application__credential_bindings__credential=credential,
            application__is_active=True,
            is_active=True,
        ).select_related('application').distinct()
        for client in clients:
            if not client_uses_credential(client, credential):
                continue
            binding = CredentialApplicationBinding.objects.get(
                credential=credential, application=client.application,
            )
            CredentialClientStatus.objects.get_or_create(binding=binding, client=client)
        states = [
            state for state in credential.rotation_statuses().select_for_update(of=('self',)).select_related('client')
            if client_uses_credential(state.client, credential) or state.is_rotation_participant
        ]
        source = credential.active_account
        target = credential.target_account
        if not target:
            raise JMSException(_('The alternating account configuration is incomplete.'))

        prepared = credential.rotation_records.filter(status='preparing', date_finished__isnull=True)
        rotation = prepared.filter(pk=rotation_id).first() if rotation_id else prepared.first()
        if rotation_id and not rotation:
            raise JMSException(_('The verified rotation cycle is no longer available.'))
        if rotation:
            rotation.status = 'running'
            rotation.save(update_fields=['status'])
        else:
            rotation = CredentialRotationRecord.objects.create(
                credential=credential, source_account=source, target_account=target,
                change_account=source, change_account_version_at_start=source.version,
                created_by=operator,
            )
        if 'participants' not in rotation.participant_snapshot:
            initialize(rotation, states)
        switched_at = timezone.now()
        rotation.participant_snapshot['source_traffic'] = {
            'no_traffic_minutes': credential.source_no_traffic_minutes,
            'operator_id': str(operator_id) if operator_id else None,
        }
        rotation.save(update_fields=['participant_snapshot'])
        credential.revision += 1
        credential.active_account = target
        credential.status = ApplicationCredential.Status.waiting_switch
        credential.change_execution = None
        credential.rotation_cancelled = False
        credential.date_rotation_started = switched_at
        credential.save(update_fields=[
            'revision', 'active_account', 'status', 'rotation_cancelled',
            'date_rotation_started', 'date_updated', 'change_execution',
        ])
        event = record(AuditEvent.ROTATION_STARTED, credential=credential, operator=operator)
        enqueue(event, ApplicationEvent.ROTATION_STARTED, rotation=rotation)
        waiting = record(
            AuditEvent.ROTATION_STEP, credential=credential, operator=operator,
            summary='Waiting for clients to apply and confirm the target account.',
        )
        enqueue(waiting, ApplicationEvent.ROTATION_WAITING, rotation=rotation)
        CredentialClientStatus.objects.filter(id__in=[state.id for state in states]).update(
            required_revision=credential.revision, is_rotation_participant=True,
        )
        from .source_traffic import start_if_ready
        start_if_ready(credential, rotation, switched_at)
        return credential

    @transaction.atomic
    def review_application_failure(self, client_id, failure_id, reason, operator):
        from rest_framework.exceptions import ValidationError
        from .source_traffic import start_if_ready
        credential = self._get_locked_credential()
        state = CredentialClientStatus.objects.select_for_update().select_related('client').filter(
            binding__credential=credential, client_id=client_id,
        ).first()
        failure = dict(state.application_failure or {}) if state else {}
        if (not failure or failure.get('id') != str(failure_id)
                or failure.get('revision') != credential.current_revision
                or failure.get('account_id') != str(credential.active_account_id)):
            raise ValidationError(_('The application failure is superseded. Refresh and review the current failure.'))
        if not failure.get('review_required'):
            return credential
        if not reason.strip():
            raise ValidationError(_('Provide a reason for continuing after the application failure.'))
        failure.update(review_required=False, reviewed_at=timezone.now().isoformat(),
                       reviewed_by=operator, reason=reason.strip())
        state.application_failure = failure
        state.save(update_fields=['application_failure', 'date_updated'])
        from accounts.models import ApplicationCommand, CredentialRotationEvent
        event = CredentialRotationEvent.objects.select_for_update().filter(source_event_id=failure['event_id']).first()
        if event is None:
            event = ApplicationCommand.objects.select_for_update().filter(source_event_id=failure['event_id']).first()
        if event:
            for recipient in event.recipients:
                if recipient['id'] == str(client_id):
                    recipient['failure_review'] = failure
            event.save(update_fields=['recipients', 'date_updated'])
        record(AuditEvent.APPLICATION_FAILURE_REVIEWED, credential=credential,
               application=state.client.application, operator=operator, source=AuditSource.ADMINISTRATOR,
               instance_id=state.client.instance_id,
               summary=reason.strip(), changes=[{'field': 'application_failure', 'before': None, 'after': failure}])
        if credential.status == credential.Status.waiting_switch:
            start_if_ready(credential)
        return credential

    @transaction.atomic
    def check_usage(self):
        from .source_traffic import blocker, notify_ready, remember, start_if_ready

        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.waiting_switch:
            raise JMSException(_('The credential policy is not waiting for the account switch.'))
        blockers = credential.get_blockers()
        if blockers:
            return credential, blockers
        traffic = start_if_ready(credential)
        if not traffic or not traffic['ready']:
            blockers.append(blocker(traffic))
        if blockers:
            return credential, blockers
        credential.status = ApplicationCredential.Status.ready_for_change
        credential.save(update_fields=['status', 'date_updated'])
        rotation = credential.rotation_records.filter(status='running', date_finished__isnull=True).first()
        event = record(
            AuditEvent.ROTATION_STEP, credential=credential, account=rotation.source_account,
            summary='Source account no-secret-fetch window completed; secret change is ready.',
        )
        remember(rotation, event, traffic)
        enqueue(event, ApplicationEvent.ROTATION_SOURCE_READY, rotation=rotation)
        operator_id = rotation.participant_snapshot['source_traffic'].get('operator_id')
        if operator_id:
            transaction.on_commit(lambda: notify_ready(credential.id, operator_id))
        return credential, []

    @transaction.atomic
    def change_secret(self):
        from .source_traffic import require_idle

        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.ready_for_change:
            raise JMSException(_('The credential policy is not ready for secret change.'))
        if credential.get_blockers():
            raise JMSException(
                detail=_('Wait for all enabled clients to apply the target account.'),
                code='credential_rotation_clients_not_ready',
            )
        require_idle(credential)
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
        if credential.get_blockers():
            return credential
        event = record(
            AuditEvent.SECRET_CHANGE_COMPLETED, credential=credential,
            summary=f'Execution {credential.change_execution_id} completed.',
        )
        enqueue(event, ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED, rotation=rotation)
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
            enqueue(event, ApplicationEvent.ROTATION_COMPLETED, rotation=rotation)
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
    def force_stop(self, reason, operator=''):
        credential = self._get_locked_credential()
        if not reason.strip():
            raise JMSException(_('Provide a reason for forcibly stopping the rotation.'))
        if credential.status != ApplicationCredential.Status.waiting_revert:
            raise JMSException(_('Only rotations waiting for account reversion can be forcibly stopped.'))
        rotation = credential.rotation_records.filter(status='running', date_finished__isnull=True).first()
        if not rotation:
            raise JMSException(_('No active rotation.'))
        rotation.participant_snapshot['force_stop'] = {
            'reason': reason.strip(), 'operator': operator,
            'stopped_at': timezone.now().isoformat(),
        }
        rotation.save(update_fields=['participant_snapshot'])
        event = record(
            AuditEvent.ROTATION_CANCELLED, credential=credential, operator=operator,
            summary=f'Rotation forcibly stopped without client recovery confirmation: {reason.strip()}',
        )
        enqueue(event, ApplicationEvent.ROTATION_FORCE_STOPPED, rotation=rotation)
        return self._finish(credential, rotation, 'cancelled')

    @transaction.atomic
    def cancel(self, reason=''):
        from .execution import outcome
        from . import preflight

        credential = self._get_locked_credential()
        if credential.status == ApplicationCredential.Status.idle:
            current = preflight.info(credential)
            if current and current['status'] == 'checking':
                preflight.fail(current['execution_id'], 'cancelled', reason)
                return credential
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
        enqueue(event, ApplicationEvent.CREDENTIAL_SWITCH_PUBLISHED, rotation=rotation)
        CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True,
        ).update(required_revision=credential.revision)
        return credential
