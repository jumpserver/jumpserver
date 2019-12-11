# coding: utf-8
#

from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .. import models

__all__ = []


class DatabaseAppPermissionSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = models.DatabaseAppPermission
        list_serializer_class = AdaptedBulkListSerializer
        fields = [

        ]
        read_only_fields = []
