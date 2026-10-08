from datetime import timedelta

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
    def prepare(self, operator='', operator_id=None):
        # Retain the old endpoint as an alias. New cycles never align accounts
        # or observe the standby account before publishing the switch.
        return self.start(operator, operator_id)

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
        if rotation and (rotation.participant_snapshot or {}).get('preparation'):
            from .preparation import _alignment
            from accounts.models import ApplicationAudit
            from django.utils.dateparse import parse_datetime
            legacy_ids = {str(value) for value in ApplicationAudit.objects.filter(
                event=AuditEvent.CREDENTIAL_FETCHED, result='success', credential_id__isnull=True,
                service_id__in=credential.applications.values('id'),
                account_id__in=(source.id, target.id),
                date_created__gte=parse_datetime(rotation.participant_snapshot['preparation']['started_at']),
            ).values_list('service_id', flat=True)}
            rotation.participant_snapshot['legacy_applications'] = [
                app for app in _alignment(credential, rotation) if app['type'] == 'api' or app['id'] in legacy_ids
            ]
            rotation.participant_snapshot['legacy_switch_started_at'] = timezone.now().isoformat()
            rotation.status = 'running'
            rotation.save(update_fields=['status', 'participant_snapshot'])
        elif rotation:
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
        if not rotation.participant_snapshot.get('preparation'):
            # Older account-secret API users cannot confirm a policy revision.
            # Require recent source-secret users to fetch the backup after
            # publication before declaring the switch applied.
            from accounts.models import ApplicationAudit
            legacy_ids = ApplicationAudit.objects.filter(
                event=AuditEvent.CREDENTIAL_FETCHED, result='success',
                credential_id__isnull=True, account_id=source.id,
                service_id__in=credential.applications.values('id'),
                date_created__gte=switched_at - timedelta(days=credential.source_no_traffic_days),
            ).values('service_id')
            rotation.participant_snapshot['legacy_applications'] = [
                {'id': str(app.id), 'name': app.name, 'type': 'api'}
                for app in credential.applications.filter(
                    is_active=True, id__in=legacy_ids,
                )
            ]
            rotation.participant_snapshot['legacy_switch_started_at'] = switched_at.isoformat()
        rotation.participant_snapshot['source_traffic'] = {
            'started_at': switched_at.isoformat(),
            'no_traffic_days': credential.source_no_traffic_days,
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
            summary='Waiting for clients to apply the target account and for source secret fetches to stop.',
        )
        enqueue(waiting, ApplicationEvent.ROTATION_WAITING, rotation=rotation)
        from .source_traffic import info as source_traffic_info, remember
        source_waiting = record(
            AuditEvent.ROTATION_STEP, credential=credential, operator=operator,
            summary='Observing JumpServer secret fetches for the source account.',
        )
        remember(rotation, source_waiting, source_traffic_info(credential, rotation, switched_at))
        enqueue(source_waiting, ApplicationEvent.ROTATION_SOURCE_WAITING, rotation=rotation)
        CredentialClientStatus.objects.filter(id__in=[state.id for state in states]).update(
            required_revision=credential.revision, is_rotation_participant=True,
        )
        return credential

    @transaction.atomic
    def check_usage(self):
        from .source_traffic import blocker, info as source_traffic_info, notify_ready, remember

        credential = self._get_locked_credential()
        if credential.status != ApplicationCredential.Status.waiting_switch:
            raise JMSException(_('The credential policy is not waiting for the account switch.'))
        blockers = credential.get_blockers()
        traffic = source_traffic_info(credential)
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
    def cancel(self, reason=''):
        from .execution import outcome
        from .preparation import PHASES, _emit
        from . import preflight

        credential = self._get_locked_credential()
        if credential.status == ApplicationCredential.Status.idle:
            current = preflight.info(credential)
            if current and current['status'] == 'checking':
                preflight.fail(current['execution_id'], 'cancelled', reason)
                return credential
        if credential.status in PHASES:
            rotation = credential.rotation_records.filter(status='preparing').first()
            if not rotation:
                raise JMSException(_('No rotation preparation is running.'))
            _emit(credential, rotation, ApplicationEvent.ROTATION_PREPARATION_CANCELLED, reason)
            return self._finish(credential, rotation, 'cancelled')
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
        if rotation.participant_snapshot.get('legacy_applications'):
            rotation.participant_snapshot['legacy_switch_started_at'] = timezone.now().isoformat()
            rotation.save(update_fields=['participant_snapshot'])
        event = record(AuditEvent.ROTATION_CANCELLED, credential=credential, summary=reason)
        credential.save(update_fields=[
            'revision', 'active_account', 'status', 'rotation_cancelled', 'date_updated',
        ])
        enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED, rotation=rotation)
        CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True,
        ).update(required_revision=credential.revision)
        return credential
