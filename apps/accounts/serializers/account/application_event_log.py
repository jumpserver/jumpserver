from rest_framework import serializers

from accounts.credential_client.commands import detail as command_detail
from accounts.const import ApplicationEvent
from accounts.models import ApplicationAudit
from .application_audit import ApplicationAuditSerializer

__all__ = ['ApplicationEventLogSerializer']


class ApplicationEventLogSerializer(serializers.ModelSerializer):
    event = serializers.CharField(source='protocol_event', read_only=True)
    event_source = serializers.CharField(read_only=True)
    published_at = serializers.DateTimeField(read_only=True)
    recipients = serializers.SerializerMethodField()
    notification_enabled = serializers.SerializerMethodField()
    requires_confirmation = serializers.SerializerMethodField()
    webhooks = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationAudit
        fields = [
            'id', 'event', 'event_source', 'published_at', 'revision',
            'service', 'service_id', 'credential', 'credential_id', 'account', 'account_id',
            'operator', 'operation_id', 'rotation_id', 'notification_enabled',
            'requires_confirmation', 'recipients', 'webhooks',
        ]
        read_only_fields = fields
        extra_kwargs = ApplicationAuditSerializer.Meta.extra_kwargs

    def get_recipients(self, instance):
        event = self.context['protocol_records'].get(instance.id)
        if instance.event_source == 'manual':
            recipients = command_detail(event)['recipients']
            recipients = [{**row, 'application': {
                'id': str(instance.service_id), 'name': instance.service,
            }} for row in recipients]
        else:
            recipients = [dict(row) for row in event.recipients]
        application = self.context.get('application_id')
        if application:
            recipients = [row for row in recipients if row['application']['id'] == application]
        return recipients

    def get_notification_enabled(self, instance):
        event = self.context['protocol_records'][instance.id]
        return True if instance.event_source == 'manual' else event.notification_enabled

    def get_requires_confirmation(self, instance):
        return instance.event_source == 'manual' or instance.protocol_event in ApplicationEvent.credential_application_events()

    def get_webhooks(self, instance):
        # Delivery metadata is safe to display; URLs, headers and bodies may
        # contain authentication material and are intentionally not returned.
        application = self.context.get('application_id')
        return [{
            'id': str(delivery.id), 'event': delivery.code,
            'application': {'id': str(delivery.audit.service_id), 'name': delivery.audit.service},
            'status': delivery.status,
            'attempts': [{
                'number': attempt.number, 'result': attempt.result,
                'status_code': attempt.status_code, 'reason': attempt.reason,
                'datetime': attempt.date_created,
            } for attempt in delivery.attempts.all()],
        } for delivery in self.context['webhook_deliveries'].get(instance.id, [])
            if not application or str(delivery.audit.service_id) == application]
