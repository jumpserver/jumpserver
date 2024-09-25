from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import Asset
from common.serializers.fields import LabeledChoiceField
from common.utils import pretty_string
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from terminal.session_lifecycle import lifecycle_events_map
from users.models import User
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
            "date_start", "date_end", "duration", "comment", "terminal_display", "is_locked",
            'command_amount', 'error_reason'
        ]
        fields_fk = ["terminal", ]
        fields_custom = ["can_replay", "can_join", "can_terminate"]
        fields = fields_small + fields_fk + fields_custom
        extra_kwargs = {
            "duration": {'label': _('Duration')},
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

    def get_fields(self):
        fields = super().get_fields()
        self.pop_fields_if_need(fields)
        return fields

    def pop_fields_if_need(self, fields):
        request = self.context.get('request')
        if request and request.method != 'GET':
            fields.pop("command_amount", None)

    def validate_asset(self, value):
        max_length = self.Meta.model.asset.field.max_length
        value = pretty_string(value, max_length=max_length)
        return value

    @staticmethod
    def get_valid_instance(model_cls, instance_id, field_name, error_message, validation_attr='is_active'):
        if instance_id is None:
            raise serializers.ValidationError({field_name: _('This field is required.')})
        instance = model_cls.objects.filter(id=instance_id).first()
        if not instance or not getattr(instance, validation_attr, False):
            raise serializers.ValidationError({field_name: error_message})
        return instance

    def create(self, validated_data):
        user_id = validated_data.get('user_id')
        asset_id = validated_data.get('asset_id')

        user = self.get_valid_instance(
            User,
            user_id,
            'user_id',
            _('No user or invalid user'),
            validation_attr='is_valid'
        )

        asset = self.get_valid_instance(
            Asset,
            asset_id,
            'asset_id',
            _('No asset or invalid asset')
        )

        validated_data['user'] = str(user)
        validated_data['asset'] = str(asset)
        return super().create(validated_data)


class SessionDisplaySerializer(SessionSerializer):
    command_amount = serializers.IntegerField(read_only=True, label=_('Command amount'))
    terminal = TerminalSmallSerializer(read_only=True, label=_('Terminal'))

    class Meta(SessionSerializer.Meta):
        fields = SessionSerializer.Meta.fields + ['command_amount', ]


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)
    version = serializers.IntegerField(write_only=True, required=False, min_value=2, max_value=5)


class SessionJoinValidateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    session_id = serializers.UUIDField()


class SessionLifecycleLogSerializer(serializers.Serializer):
    event = serializers.ChoiceField(choices=list(lifecycle_events_map.keys()))
    reason = serializers.CharField(required=False)
    user = serializers.CharField(required=False)
