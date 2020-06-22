from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.serializers import AdaptedBulkListSerializer
from ..models import Session

__all__ = [
    'SessionSerializer', 'SessionDisplaySerializer',
    'ReplaySerializer', 'SessionJoinValidateSerializer',
]


class SessionSerializer(BulkOrgResourceModelSerializer):
    org_id = serializers.CharField(allow_blank=True)

    class Meta:
        model = Session
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            "id", "user", "asset", "system_user",
            "user_id", "asset_id", "system_user_id",
            "login_from", "login_from_display", "remote_addr",
            "is_success",  "is_finished", "has_replay", "can_replay",
            "can_join", "protocol", "date_start", "date_end",
            "terminal",
        ]
        extra_kwargs = {
            "protocol": {'label': _('Protocol')},
            'is_finished': {'label': _('Is finished')}
        }


class SessionDisplaySerializer(SessionSerializer):
    command_amount = serializers.IntegerField(read_only=True)

    class Meta(SessionSerializer.Meta):
        fields = SessionSerializer.Meta.fields + ['command_amount']


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)


class SessionJoinValidateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    session_id = serializers.UUIDField()
