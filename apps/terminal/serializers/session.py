from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from common.utils import pretty_string
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from terminal.session_lifecycle import lifecycle_events_map
from .terminal import TerminalSmallSerializer
from ..const import SessionType, SessionErrorReason
from ..models import Session

__all__ = [
    'SessionSerializer', 'SessionDisplaySerializer',
    'ReplaySerializer', 'SessionJoinValidateSerializer',
    'SessionLifecycleLogSerializer'
]


class SessionSerializer(BulkOrgResourceModelSerializer):
    org_id = serializers.CharField(allow_blank=True)
    protocol = serializers.CharField(max_length=128, label=_("Protocol"))
    type = LabeledChoiceField(
        choices=SessionType.choices, label=_("Type"), default=SessionType.normal
    )
    can_replay = serializers.BooleanField(read_only=True, label=_("Can replay"))
    can_join = serializers.BooleanField(read_only=True, label=_("Can join"))
    can_terminate = serializers.BooleanField(read_only=True, label=_("Can terminate"))
    asset = serializers.CharField(label=_("Asset"), style={'base_template': 'textarea.html'})
    error_reason = LabeledChoiceField(
        choices=SessionErrorReason.choices, label=_("Error reason"), required=False
    )

    class Meta:
        model = Session
        fields_mini = ["id"]
        fields_small = fields_mini + [
            "user", "asset", "user_id", "asset_id", 'account', 'account_id',
            "protocol", 'type', "login_from", "remote_addr",
            "is_success", "is_finished", "has_replay", "has_command",
            "date_start", "date_end", "comment", "terminal_display", "is_locked",
            'command_amount', 'error_reason'
        ]
        fields_fk = ["terminal", ]
        fields_custom = ["can_replay", "can_join", "can_terminate"]
        fields = fields_small + fields_fk + fields_custom
        extra_kwargs = {
            "protocol": {'label': _('Protocol')},
            'user_id': {'label': _('User ID')},
            'asset_id': {'label': _('Asset ID')},
            'login_from_display': {'label': _('Login from display')},
            'is_success': {'label': _('Is success')},
            'can_replay': {'label': _('Can replay')},
            'can_join': {'label': _('Can join')},
            'terminal': {'label': _('Terminal')},
            'is_finished': {'label': _('Is finished')},
            'can_terminate': {'label': _('Can terminate')},
            'terminal_display': {'label': _('Terminal display')},
        }

    def validate_asset(self, value):
        max_length = self.Meta.model.asset.field.max_length
        value = pretty_string(value, max_length=max_length)
        return value


class SessionDisplaySerializer(SessionSerializer):
    command_amount = serializers.IntegerField(read_only=True, label=_('Command amount'))
    terminal = TerminalSmallSerializer(read_only=True, label=_('Terminal'))

    class Meta(SessionSerializer.Meta):
        fields = SessionSerializer.Meta.fields + ['command_amount', ]


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)
    version = serializers.IntegerField(write_only=True, required=False, min_value=2, max_value=4)


class SessionJoinValidateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    session_id = serializers.UUIDField()


class SessionLifecycleLogSerializer(serializers.Serializer):
    event = serializers.ChoiceField(choices=list(lifecycle_events_map.keys()))
    reason = serializers.CharField(required=False)
    user = serializers.CharField(required=False)
