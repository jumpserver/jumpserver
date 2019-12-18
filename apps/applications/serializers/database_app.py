# coding: utf-8
#

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.serializers import AdaptedBulkListSerializer

from .. import models

__all__ = [
    'DatabaseAppSerializer',
]


class DatabaseAppSerializer(BulkOrgResourceModelSerializer):

    class Meta:
        model = models.DatabaseApp
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'type', 'get_type_display', 'host', 'port',
            'database', 'comment', 'created_by', 'date_created', 'date_updated',
        ]
        read_only_fields = [
            'created_by', 'date_created', 'date_updated'
            'get_type_display',
        ]
