# coding: utf-8
#

import copy
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.serializers import AdaptedBulkListSerializer
from common.fields.serializer import CustomMetaDictField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.models import Asset

from .. import const
from ..models import RemoteApp


class RemmoteAppCategorySerializer(serializers.Serializer):
    asset = serializers.CharField(max_length=36, label=_('Assets'))


class RemoteAppAttrsSerializer(RemmoteAppCategorySerializer):
    path = serializers.CharField(label=_('Remote App path'))


class ChromeAttrsSerializer(RemoteAppAttrsSerializer):
    REMOTE_APP_PATH = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    path = serializers.CharField(label=_('Remote App path'), default=REMOTE_APP_PATH)
    chrome_target = serializers.CharField(label=_('Target URL'))
    chrome_username = serializers.CharField(label=_('Username'))
    chrome_password = serializers.CharField(write_only=True, label=_('Password'))


class MySQLWorkbenchAttrsSerializer(RemoteAppAttrsSerializer):
    REMOTE_APP_PATH = 'C:\Program Files\MySQL\MySQL Workbench 8.0 CE\MySQLWorkbench.exe'
    path = serializers.CharField(label=_('Remote App path'), default=REMOTE_APP_PATH)
    mysql_workbench_ip = serializers.CharField(label=_('IP'))
    mysql_workbench_port = serializers.IntegerField(label=_('Port'))
    mysql_workbench_name = serializers.CharField(label=_('Database'))
    mysql_workbench_username = serializers.CharField(label=_('Username'))
    mysql_workbench_password = serializers.CharField(write_only=True, label=_('Password'))


class VMwareClientAttrsSerializer(RemoteAppAttrsSerializer):
    REMOTE_APP_PATH = 'C:\Program Files (x86)\VMware\Infrastructure\Virtual Infrastructure Client\Launcher\VpxClient.exe'
    path = serializers.CharField(label=_('Remote App path'), default=REMOTE_APP_PATH)
    vmware_target = serializers.CharField(label=_('Target URL'))
    vmware_username = serializers.CharField(label=_('Username'))
    vmware_password = serializers.CharField(write_only=True, label=_('Password'))


class CustomRemoteAppAttrsSeralizers(RemoteAppAttrsSerializer):
    custom_cmdline = serializers.CharField(label=_('Operating parameter'))
    custom_target = serializers.CharField(label=_('Target url'))
    custom_username = serializers.CharField(label=_('Username'))
    custom_password = serializers.CharField(write_only=True, label=_('Password'))


class RemoteAppParamsDictField(CustomMetaDictField):
    type_fields_map = const.REMOTE_APP_TYPE_FIELDS_MAP
    default_type = const.REMOTE_APP_TYPE_CHROME
    convert_key_remove_type_prefix = False
    convert_key_to_upper = False


class RemoteAppSerializer(BulkOrgResourceModelSerializer):
    params = RemoteAppParamsDictField()
    type_fields_map = const.REMOTE_APP_TYPE_FIELDS_MAP

    class Meta:
        model = RemoteApp
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'asset', 'asset_info', 'type', 'get_type_display',
            'path', 'params', 'date_created', 'created_by', 'comment',
        ]
        read_only_fields = [
            'created_by', 'date_created', 'asset_info',
            'get_type_display'
        ]

    def process_params(self, instance, validated_data):
        new_params = copy.deepcopy(validated_data.get('params', {}))
        tp = validated_data.get('type', '')

        if tp != instance.type:
            return new_params

        old_params = instance.params
        fields = self.type_fields_map.get(instance.type, [])
        for field in fields:
            if not field.get('write_only', False):
                continue
            field_name = field['name']
            new_value = new_params.get(field_name, '')
            old_value = old_params.get(field_name, '')
            field_value = new_value if new_value else old_value
            new_params[field_name] = field_value

        return new_params

    def update(self, instance, validated_data):
        params = self.process_params(instance, validated_data)
        validated_data['params'] = params
        return super().update(instance, validated_data)


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
