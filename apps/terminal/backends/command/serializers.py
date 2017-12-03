# ~*~ coding: utf-8 ~*~
from rest_framework import serializers


class SessionCommandSerializer(serializers.Serializer):
    """使用这个类作为基础Command Log Serializer类, 用来序列化"""

    id = serializers.UUIDField(read_only=True)
    user = serializers.CharField(max_length=64)
    asset = serializers.CharField(max_length=128)
    system_user = serializers.CharField(max_length=64)
    input = serializers.CharField(max_length=128)
    output = serializers.CharField(max_length=1024, allow_blank=True)
    session = serializers.CharField(max_length=36)
    timestamp = serializers.IntegerField()

