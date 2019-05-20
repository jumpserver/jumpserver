# coding: utf-8
#


from rest_framework import serializers

from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer

from .. import const
from ..models import RemoteApp


__all__ = [
    'RemoteAppSerializer', 'RemoteAppConnectionInfoSerializer',
]


class RemoteAppParamsDictField(serializers.DictField):
    """
    RemoteApp field => params
    """
    @staticmethod
    def filter_attribute(attribute, instance):
        """
        过滤掉params字段值中write_only特性的key-value值
        For example, the chrome_password field is not returned when serializing
        {
            'chrome_target': 'http://www.jumpserver.org/',
            'chrome_username': 'admin',
            'chrome_password': 'admin',
        }
        """
        for field in const.REMOTE_APP_TYPE_MAP_FIELDS[instance.type]:
            if field.get('write_only', False):
                attribute.pop(field['name'], None)
        return attribute

    def get_attribute(self, instance):
        """
        序列化时调用
        """
        attribute = super().get_attribute(instance)
        attribute = self.filter_attribute(attribute, instance)
        return attribute

    @staticmethod
    def filter_value(dictionary, value):
        """
        过滤掉不属于当前app_type所包含的key-value值
        """
        app_type = dictionary.get('type', const.REMOTE_APP_TYPE_CHROME)
        fields = const.REMOTE_APP_TYPE_MAP_FIELDS[app_type]
        fields_names = [field['name'] for field in fields]
        no_need_keys = [k for k in value.keys() if k not in fields_names]
        for k in no_need_keys:
            value.pop(k)
        return value

    def get_value(self, dictionary):
        """
        反序列化时调用
        """
        value = super().get_value(dictionary)
        value = self.filter_value(dictionary, value)
        return value


class RemoteAppSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    params = RemoteAppParamsDictField()

    class Meta:
        model = RemoteApp
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'asset', 'system_user', 'type', 'path', 'params',
            'comment', 'created_by', 'date_created', 'asset_info',
            'system_user_info', 'get_type_display',
        ]
        read_only_fields = [
            'created_by', 'date_created', 'asset_info',
            'system_user_info', 'get_type_display'
        ]


class RemoteAppConnectionInfoSerializer(serializers.ModelSerializer):
    parameter_remote_app = serializers.SerializerMethodField()

    class Meta:
        model = RemoteApp
        fields = [
            'id', 'name', 'asset', 'system_user', 'parameter_remote_app',
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
