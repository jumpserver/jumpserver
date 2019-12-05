# coding: utf-8
#


from rest_framework import serializers

from common.serializers import AdaptedBulkListSerializer
from common.fields.serializer import CustomMetaDictField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .. import const
from ..models import RemoteApp


__all__ = [
    'RemoteAppSerializer', 'RemoteAppConnectionInfoSerializer',
]


class RemoteAppParamsDictField(CustomMetaDictField):
    type_map_fields = const.REMOTE_APP_TYPE_MAP_FIELDS
    default_type = const.REMOTE_APP_TYPE_CHROME


class RemoteAppSerializer(BulkOrgResourceModelSerializer):
    params = RemoteAppParamsDictField()

    class Meta:
        model = RemoteApp
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'asset', 'type', 'path', 'params',
            'comment', 'created_by', 'date_created', 'asset_info',
            'get_type_display',
        ]
        read_only_fields = [
            'created_by', 'date_created', 'asset_info',
            'get_type_display'
        ]


class RemoteAppConnectionInfoSerializer(serializers.ModelSerializer):
    parameter_remote_app = serializers.SerializerMethodField()

    class Meta:
        model = RemoteApp
        fields = [
            'id', 'name', 'asset', 'parameter_remote_app',
        ]
        read_only_fields = ['parameter_remote_app']

    @staticmethod
    def get_parameter_remote_app(obj):
        parameter = {
            'program': const.REMOTE_APP_BOOT_PROGRAM_NAME,
            'working_directory': '',
            'parameters': obj.parameters,
        }
        return parameter
