# coding: utf-8
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.serializers import AdaptedBulkListSerializer

from .. import models


class DatabaseAttrsSerializer(serializers.Serializer):
    host = serializers.CharField()
    port = serializers.IntegerField()
    database = serializers.CharField(allow_blank=True, allow_null=True)


class MySQLAttrsSerializer(DatabaseAttrsSerializer):
    port = serializers.IntegerField(default=3306, label=_('Port'))


class PostgreAttrsSerializer(DatabaseAttrsSerializer):
    port = serializers.IntegerField(default=5432)


class OracleAttrsSerializer(DatabaseAttrsSerializer):
    port = serializers.IntegerField(default=1521)


class MariaDBAttrsSerializer(MySQLAttrsSerializer):
    pass


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
