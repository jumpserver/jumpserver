from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..resources import RequestSerializer as BaseRequestSerializer


class RequestSerializer(BaseRequestSerializer):
    session = serializers.UUIDField(label=_('Session ID'))
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=3600, label=_('Validity (seconds)'))

    def validate_session(self, value):
        from terminal.models import Session
        from orgs.utils import tmp_to_org
        user = self.context['request'].user
        with tmp_to_org(self.context['org_id']):
            sessions = Session.objects.filter(pk=value, org_id=self.context['org_id'])
            if not user.has_perm('terminal.view_session'):
                sessions = sessions.filter(user_id=str(user.pk))
            if not sessions.exists():
                raise serializers.ValidationError(_('Select an accessible session in this organization.'))
        return value
