# coding: utf-8
#


from rest_framework import serializers

from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer

from .. import const
from ..models import RemoteApp


__all__ = [
    'RemoteAppSerializer',
]


class RemoteAppTypeParamsDictField(serializers.DictField):

    @staticmethod
    def filter_attribute(attribute, instance):
        """
        过滤掉params字段值中write_only特性的key-value值
        """
        fields = const.REMOTE_APP_TYPE_MAP_FIELDS[instance.type]
        for field in fields:
            if field.get('write_only', False):
                attribute.pop(field['name'], None)
        return attribute

    def get_attribute(self, instance):
        """
        序列化时调用
        For example, the chrome_password field is not returned when serializing
        {
            'chrome_target': 'http://www.jumpserver.org/',
            'chrome_username': 'admin',
            'chrome_password': 'admin',
        }
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

    params = RemoteAppTypeParamsDictField()

    class Meta:
        model = RemoteApp
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'asset', 'system_user', 'type', 'path', 'params',
            'comment', 'created_by', 'date_created',
        ]
