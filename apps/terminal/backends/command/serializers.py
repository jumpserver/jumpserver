# ~*~ coding: utf-8 ~*~
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from .models import AbstractSessionCommand


class SessionCommandSerializer(serializers.Serializer):
    """使用这个类作为基础Command Log Serializer类, 用来序列化"""

    id = serializers.UUIDField(read_only=True)
    user = serializers.CharField(max_length=64, label=_("User"))
    asset = serializers.CharField(max_length=128, label=_("Asset"))
    system_user = serializers.CharField(max_length=64, label=_("System user"))
    input = serializers.CharField(max_length=128, label=_("Command"))
    output = serializers.CharField(max_length=1024, allow_blank=True, label=_("Output"))
    session = serializers.CharField(max_length=36, label=_("Session"))
    risk_level = serializers.ChoiceField(required=False, label=_("Risk level"), choices=AbstractSessionCommand.RISK_LEVEL_CHOICES)
    risk_level_display = serializers.SerializerMethodField()
    org_id = serializers.CharField(max_length=36, required=False, default='', allow_null=True, allow_blank=True)
    timestamp = serializers.IntegerField()

    @staticmethod
    def get_risk_level_display(obj):
        risk_mapper = dict(AbstractSessionCommand.RISK_LEVEL_CHOICES)
        return risk_mapper.get(obj.risk_level)
