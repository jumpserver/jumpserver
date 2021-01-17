# coding: utf-8
#
from rest_framework import serializers
from common.utils import get_logger
from ..models import Application


logger = get_logger(__file__)


__all__ = ['RemoteAppConnectionInfoSerializer']


class RemoteAppConnectionInfoSerializer(serializers.ModelSerializer):
    parameter_remote_app = serializers.SerializerMethodField()
    asset = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'name', 'asset', 'parameter_remote_app',
        ]
        read_only_fields = ['parameter_remote_app']

    @staticmethod
    def get_asset(obj):
        return obj.attrs.get('asset')

    @staticmethod
    def get_parameters(obj):
        """
        返回Guacamole需要的RemoteApp配置参数信息中的parameters参数
        """
        from .attrs import get_serializer_class_by_application_type
        serializer_class = get_serializer_class_by_application_type(obj.type)
        fields = serializer_class().get_fields()

        parameters = [obj.type]
        for field_name in list(fields.keys()):
            if field_name in ['asset']:
                continue
            value = obj.attrs.get(field_name)
            if not value:
                continue
            if field_name == 'path':
                value = '\"%s\"' % value
            parameters.append(str(value))

        parameters = ' '.join(parameters)
        return parameters

    def get_parameter_remote_app(self, obj):
        return {
            'program': '||jmservisor',
            'working_directory': '',
            'parameters': self.get_parameters(obj)
        }
