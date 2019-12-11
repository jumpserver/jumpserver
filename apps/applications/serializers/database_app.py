# coding: utf-8
#

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.serializers import AdaptedBulkListSerializer

from .. import models

__all__ = [
    'DatabaseAppSerializer'
]


class DatabaseAppSerializer(BulkOrgResourceModelSerializer):

    class Meta:
        model = models.DatabaseApp
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'type', 'get_type_display', 'host', 'port', 'database',
            'login_mode', 'user', 'password', 'comment',
            'created_by', 'date_created', 'date_updated',
        ]
        read_only_fields = [
            'created_by', 'date_created', 'date_updated'
            'get_type_display'
        ]

    @staticmethod
    def clean_password_field(validated_data):
        value = validated_data.get('password')
        if not value:
            validated_data.pop('password', None)

    def update(self, instance, validated_data):
        self.clean_password_field(validated_data)
        return super().update(instance, validated_data)
