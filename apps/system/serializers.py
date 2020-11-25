from common.drf.serializers import BulkModelSerializer

from .models import Stat


class StatSerializer(BulkModelSerializer):
    class Meta:
        model = Stat
        fields = (
            'id', 'node', 'ip', 'component',
            'key', 'value', 'datetime',
        )
