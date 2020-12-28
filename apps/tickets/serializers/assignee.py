from rest_framework import serializers

__all__ = ['AssigneeSerializer']


class AssigneeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    username = serializers.CharField()
