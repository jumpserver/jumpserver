from rest_framework import serializers

from accounts.models import ApplicationAudit

__all__ = ['ApplicationAuditSerializer']


class ApplicationAuditSerializer(serializers.ModelSerializer):
    datetime = serializers.DateTimeField(source='date_created', read_only=True)
    notification = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationAudit
        fields = [
            'id', 'event', 'result', 'service', 'service_id', 'credential', 'credential_id',
            'credential_key', 'configuration', 'configuration_id', 'instance_id',
            'source', 'operator', 'remote_addr', 'revision', 'rotation_id', 'summary',
            'changes', 'datetime', 'notification',
        ]
        read_only_fields = fields

    def get_notification(self, instance):
        if self.context['view'].action != 'retrieve' or not hasattr(instance, 'delivery'):
            return None
        delivery = instance.delivery
        return {
            'url': delivery.url, 'event': delivery.code, 'event_id': str(delivery.event_id),
            'attempts': [{
                'id': attempt.number, 'datetime': attempt.date_created,
                'result': attempt.result, 'status_code': attempt.status_code, 'reason': attempt.reason,
            } for attempt in delivery.attempts.all()],
        }
