from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.serializers import AdaptedBulkListSerializer
from ..models import Session


class SessionSerializer(BulkOrgResourceModelSerializer):
    command_amount = serializers.IntegerField(read_only=True)
    org_id = serializers.CharField(allow_blank=True)

    class Meta:
        model = Session
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            "id", "user", "asset", "system_user", "login_from",
            "login_from_display", "remote_addr", "is_finished",
            "has_replay", "can_replay", "protocol", "date_start", "date_end",
            "terminal", "command_amount",
        ]


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)
