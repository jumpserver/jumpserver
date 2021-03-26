from common.drf.serializers import BulkModelSerializer
from .. import models


__all__ = ['RoleSerializer']


class RoleSerializer(BulkModelSerializer):

    class Meta:
        model = models.Role
        fields = [
            'id', 'display_name', 'name', 'type', 'permissions', 'is_builtin', 'comment',
            'created_by', 'date_created', 'date_updated'
        ]
        extra_kwargs = {
            'created_by': {'read_only': True},
            'date_created': {'read_only': True},
            'date_updated': {'read_only': True},
            'is_builtin': {'read_only': True}
        }
