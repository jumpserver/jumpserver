# coding: utf-8
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.serializers import AdaptedBulkListSerializer

from .. import models


class DBAttrsSerializer(serializers.Serializer):
    host = serializers.CharField(max_length=128, label=_('Host'))
    port = serializers.IntegerField(label=_('Port'))
    database = serializers.CharField(max_length=128, required=True, label=_('Database'))


class MySQLAttrsSerializer(DBAttrsSerializer):
    port = serializers.IntegerField(default=3306, label=_('Port'))


class PostgreAttrsSerializer(DBAttrsSerializer):
    port = serializers.IntegerField(default=5432, label=_('Port'))


class OracleAttrsSerializer(DBAttrsSerializer):
    port = serializers.IntegerField(default=1521, label=_('Port'))


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
        extra_kwargs = {
            'get_type_display': {'label': _('Type for display')},
        }
