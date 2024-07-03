import time

from rest_framework import serializers

__all__ = [
    'LokiLogSerializer',
]


class LokiLogSerializer(serializers.Serializer):
    components = serializers.CharField(required=False, )
    start = serializers.IntegerField()
    end = serializers.IntegerField(default=time.time)
    search = serializers.CharField(required=False, default='')
