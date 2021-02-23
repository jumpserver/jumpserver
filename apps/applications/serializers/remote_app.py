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
    def get_parameter_remote_app(obj):
        return obj.get_rdp_remote_app_setting()
