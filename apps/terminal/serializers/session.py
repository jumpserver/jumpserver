from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Session

__all__ = [
    'SessionSerializer', 'SessionDisplaySerializer',
    'ReplaySerializer', 'SessionJoinValidateSerializer',
]


class SessionSerializer(BulkOrgResourceModelSerializer):
    org_id = serializers.CharField(allow_blank=True)
    terminal_display = serializers.CharField(read_only=True, label=_('Terminal display'))

    class Meta:
        model = Session
        fields_mini = ["id"]
        fields_small = fields_mini + [
            "user", "asset", "system_user",
            "user_id", "asset_id", "system_user_id",
            "login_from", "login_from_display", "remote_addr", "protocol",
            "is_success", "is_finished", "has_replay",
            "date_start", "date_end",
        ]
        fields_fk = ["terminal", ]
        fields_custom = ["can_replay", "can_join", "can_terminate", 'terminal_display']
        fields = fields_small + fields_fk + fields_custom
        extra_kwargs = {
            "protocol": {'label': _('Protocol')},
            'user_id': {'label': _('User ID')},
            'asset_id': {'label': _('Asset ID')},
            'system_user_id': {'label': _('System user ID')},
            'login_from_display': {'label': _('Login from display')},
            'is_success': {'label': _('Is success')},
            'can_replay': {'label': _('Can replay')},
            'can_join': {'label': _('Can join')},
            'terminal': {'label': _('Terminal ID')},
            'is_finished': {'label': _('Is finished')},
            'can_terminate': {'label': _('Can terminate')},
            'terminal_display': {'label': _('Terminal display')},
        }


class SessionDisplaySerializer(SessionSerializer):
    command_amount = serializers.IntegerField(read_only=True, label=_('Command amount'))

    class Meta(SessionSerializer.Meta):
        fields = SessionSerializer.Meta.fields + ['command_amount', ]


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)
    version = serializers.IntegerField(write_only=True, required=False, min_value=2, max_value=3)


class SessionJoinValidateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    session_id = serializers.UUIDField()
