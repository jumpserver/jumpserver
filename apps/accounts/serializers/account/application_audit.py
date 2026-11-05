from rest_framework import serializers
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from accounts.models import ApplicationAudit
from accounts.webhooks import mask_webhook_url

__all__ = ['ApplicationAuditSerializer']


class ApplicationAuditSerializer(serializers.ModelSerializer):
    datetime = serializers.DateTimeField(source='date_created', read_only=True)
    notification = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationAudit
        fields = [
            'id', 'event', 'result', 'service', 'service_id', 'credential', 'credential_id',
            'credential_key', 'account', 'account_id',
            'instance_id',
            'source', 'operator', 'remote_addr', 'revision', 'rotation_id', 'operation_id', 'summary',
            'changes', 'datetime', 'notification',
        ]
        read_only_fields = fields
        extra_kwargs = {
            'id': {'label': _('ID')},
            'event': {'label': _('Event')},
            'service': {'label': _('Application')},
            'service_id': {'label': _('Application ID')},
            'credential': {'label': _('Credential policy')},
            'credential_id': {'label': _('Credential ID')},
            'credential_key': {'label': _('Credential key')},
            'account': {'label': _('Account')},
            'account_id': {'label': format_lazy('{} ID', _('Account'))},
            'instance_id': {'label': _('Instance ID')},
            'operator': {'label': _('Operator')},
            'remote_addr': {'label': _('Remote Address')},
            'source': {'label': _('Source')},
            'result': {'label': _('Result')},
            'revision': {'label': _('Revision')},
            'rotation_id': {'label': _('Rotation ID')},
            'operation_id': {'label': format_lazy('{} ID', _('Operation'))},
            'summary': {'label': _('Detail')},
        }

    def get_notification(self, instance):
        if self.context['view'].action != 'retrieve' or not hasattr(instance, 'delivery'):
            return None
        delivery = instance.delivery
        url = mask_webhook_url(delivery.url) if delivery.method else delivery.url
        return {
            'url_display': url, 'event': delivery.code, 'event_id': str(delivery.event_id),
            'attempts': [{
                'id': attempt.number, 'datetime': attempt.date_created,
                'result': attempt.result, 'status_code': attempt.status_code, 'reason': attempt.reason,
            } for attempt in delivery.attempts.all()],
        }
