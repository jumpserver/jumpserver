# ~*~ coding: utf-8 ~*~
from rest_framework import serializers


class InsecureCommandAlertSerializer(serializers.Serializer):
    input = serializers.CharField()
    asset = serializers.CharField()
    user = serializers.CharField()
    risk_level = serializers.IntegerField()
    session = serializers.UUIDField()
