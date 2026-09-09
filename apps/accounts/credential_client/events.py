"""Per-instance application event delivery and retry handling."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.const import AuditEvent, AuditSource, ApplicationEvent
from accounts.models import (
    ApplicationAudit, ApplicationEventDelivery, ApplicationEventAttempt,
    ApplicationCredential, CredentialClientInstance,
)
from .audit import record


def enqueue(event, code, clients=None):
    if clients is None:
        clients = CredentialClientInstance.objects.filter(
            configuration__credentials=event.credential_id,
        )
    revoked_client_ids = (
        list(clients.values_list('id', flat=True).distinct())
        if code == ApplicationEvent.ACCESS_REVOKED else []
    )
    clients = list(clients.filter(
        is_active=True, application__is_active=True,
        configuration__is_active=True, configuration__notification_enabled=True,
        events_enabled=True,
    ).select_related('application', 'configuration').distinct())
    if revoked_client_ids:
        with transaction.atomic():
            stale = ApplicationEventDelivery.objects.select_for_update().filter(
                client_id__in=revoked_client_ids,
                event__credential_id=event.credential_id,
                status='pending',
            ).exclude(code=ApplicationEvent.ACCESS_REVOKED)
            for delivery in stale:
                ClientEventManager._finish(delivery, 'failed', 'Credential access was revoked.')
    for client in clients:
        if ApplicationEventDelivery.objects.filter(event=event, client=client).exists():
            continue
        source = AuditSource.SDK if client.type == CredentialClientInstance.Type.sdk else AuditSource.AGENT
        audit = record(
            AuditEvent.NOTIFICATION, client=client, result='pending',
            source=source, operator=source,
            credential=ApplicationCredential.objects.filter(id=event.credential_id).first(),
            summary='Waiting for client delivery.',
        )
        ApplicationEventDelivery.objects.create(
            event=event, audit=audit, client=client, code=code,
            url=client.configuration.notification_url if client.type == CredentialClientInstance.Type.agent else '',
            expires_at=timezone.now() + timedelta(minutes=10),
        )


class ClientEventManager:
    def __init__(self, manager):
        self.manager = manager
        self.client = manager.client

    def subscribe(self, enabled):
        client = CredentialClientInstance.objects.select_for_update().get(id=self.client.id)
        enabled = enabled and self.manager.configuration.notification_enabled
        changed = client.events_enabled != enabled
        client.events_enabled = enabled
        client.save(update_fields=['events_enabled'])
        self.client.events_enabled = enabled
        if not enabled:
            self._finish_pending('Event listener stopped.')
        elif changed:
            for item in self.manager.configuration.credentials.all():
                try:
                    credential = self.manager._get_credential(item.key, lock=False)
                except (PermissionDenied, ValidationError):
                    continue
                event = record(AuditEvent.SUBSCRIPTION_SNAPSHOT, credential=credential, client=client)
                code = ApplicationEvent.CREDENTIAL_UNAVAILABLE if (
                    credential.rotation_mode == 'single' and credential.status == 'changing_secret'
                ) else ApplicationEvent.CREDENTIAL_PUBLISHED
                enqueue(event, code, CredentialClientInstance.objects.filter(id=client.id))
        return {'enabled': enabled}

    def _finish_pending(self, reason):
        deliveries = ApplicationEventDelivery.objects.filter(client=self.client, status='pending')
        for delivery in deliveries.select_for_update():
            self._finish(delivery, 'failed', reason)

    @staticmethod
    def _finish(delivery, result, reason):
        delivery.status = result
        delivery.save(update_fields=['status'])
        delivery.attempts.filter(result='pending').update(result='failed', reason=reason[:128])
        ApplicationAudit.objects.filter(id=delivery.audit_id).update(result=result, summary=reason)

    def poll(self):
        if not self.client.events_enabled or not self.manager.configuration.notification_enabled:
            return {'enabled': False, 'events': []}
        self.manager._touch(timezone.now())
        # One claim per poll keeps the worker serial, while credentials remain independent.
        deliveries = ApplicationEventDelivery.objects.select_for_update(of=('self',)).filter(
            client=self.client, status='pending', available_at__lte=timezone.now(),
        ).select_related('event').order_by('date_created', 'id')
        for delivery in deliveries:
            previous = delivery.attempts.order_by('-number').first()
            number = previous.number + 1 if previous else 1
            if previous and previous.result == 'pending':
                previous.result, previous.reason = 'failed', 'Client delivery lease expired.'
                previous.save(update_fields=['result', 'reason'])
            if delivery.expires_at <= timezone.now() or number > 5:
                self._finish(delivery, 'failed', 'Notification retry limit or deadline reached.')
                continue
            # Revocation events contain only the instance's former binding, never credentials.
            if delivery.code != ApplicationEvent.ACCESS_REVOKED:
                try:
                    self.manager._get_credential(delivery.event.credential_key, lock=False)
                except (PermissionDenied, ValidationError):
                    self._finish(delivery, 'failed', 'Credential access was revoked.')
                    continue
            attempt = ApplicationEventAttempt.objects.create(delivery=delivery, number=number)
            delivery.available_at = timezone.now() + timedelta(seconds=60)
            delivery.save(update_fields=['available_at'])
            return {'enabled': True, 'events': [{
                'delivery_id': str(delivery.id), 'attempt_id': str(attempt.id),
                'event_id': str(delivery.event_id), 'event': delivery.code,
                'instance_id': self.client.instance_id,
                'client_id': str(self.client.id),
                'configuration_id': str(self.client.configuration_id),
                'key': delivery.event.credential_key, 'revision': delivery.event.revision,
                'occurred_at': delivery.event.date_created,
            }]}
        return {'enabled': True, 'events': []}

    def report(self, attempt_id, result, status_code=None, reason=''):
        attempt = ApplicationEventAttempt.objects.filter(
            id=attempt_id, delivery__client=self.client,
        ).first()
        if not attempt:
            raise ValidationError('Notification attempt not found.')
        delivery = ApplicationEventDelivery.objects.select_for_update().get(id=attempt.delivery_id)
        attempt.refresh_from_db()
        if attempt.result != 'pending':
            return {'result': attempt.result}
        if delivery.status != 'pending':
            raise ValidationError('Notification delivery is already closed.')
        if delivery.expires_at <= timezone.now():
            self._finish(delivery, 'failed', 'Notification delivery deadline reached.')
            return {'result': 'failed'}
        if self.client.type == CredentialClientInstance.Type.agent and result == 'success' and not (status_code and 200 <= status_code < 300):
            raise ValidationError('HTTP success requires a 2xx status code.')
        attempt.result, attempt.status_code = result, status_code
        # Reasons are controlled codes; callback exception text / HTTP bodies can contain secrets.
        attempt.reason = reason
        attempt.save(update_fields=['result', 'status_code', 'reason'])
        if result == 'success':
            self._finish(delivery, result, 'Notification delivered; application confirmation is separate.')
        elif attempt.number >= 5:
            self._finish(delivery, 'failed', 'Notification retry limit reached.')
        else:
            delivery.available_at = timezone.now() + timedelta(seconds=[5, 15, 30, 60][attempt.number - 1])
            delivery.save(update_fields=['available_at'])
            ApplicationAudit.objects.filter(id=delivery.audit_id).update(
                result='retrying', summary='Notification failed; waiting for retry.',
            )
        return {'result': result}
