# coding: utf-8
#

import copy
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from common.serializers import AdaptedBulkListSerializer
from common.fields.serializer import CustomMetaDictField
from common.utils import get_logger
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.models import Asset

from .. import const
from ..models import RemoteApp, Category, Application

logger = get_logger(__file__)


class CharPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):

    def to_internal_value(self, data):
        instance = super().to_internal_value(data)
        return str(instance.id)

    def to_representation(self, value):
        # value is instance.id
        if self.pk_field is not None:
            return self.pk_field.to_representation(value)
        return value


class RemoteAppAttrsSerializer(serializers.Serializer):
    asset_info = serializers.SerializerMethodField()
    asset = CharPrimaryKeyRelatedField(queryset=Asset.objects, required=False, label=_("Asset"))
    path = serializers.CharField(max_length=128, label=_('Application path'))

    @staticmethod
    def get_asset_info(obj):
        asset_info = {}
        asset_id = obj.get('asset')
        if not asset_id:
            return asset_info
        try:
            asset = Asset.objects.get(id=asset_id)
            asset_info.update({
                'id': str(asset.id),
                'hostname': asset.hostname
            })
        except ObjectDoesNotExist as e:
            logger.error(e)
        return asset_info


class ChromeAttrsSerializer(RemoteAppAttrsSerializer):
    REMOTE_APP_PATH = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    path = serializers.CharField(max_length=128, label=_('Application path'), default=REMOTE_APP_PATH)
    chrome_target = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Target URL'))
    chrome_username = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Username'))
    chrome_password = serializers.CharField(max_length=128, allow_blank=True, required=False, write_only=True, label=_('Password'))


class MySQLWorkbenchAttrsSerializer(RemoteAppAttrsSerializer):
    REMOTE_APP_PATH = 'C:\Program Files\MySQL\MySQL Workbench 8.0 CE\MySQLWorkbench.exe'
    path = serializers.CharField(max_length=128, label=_('Application path'), default=REMOTE_APP_PATH)
    mysql_workbench_ip = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('IP'))
    mysql_workbench_port = serializers.IntegerField(required=False, label=_('Port'))
    mysql_workbench_name = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Database'))
    mysql_workbench_username = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Username'))
    mysql_workbench_password = serializers.CharField(max_length=128, allow_blank=True, required=False, write_only=True, label=_('Password'))


class VMwareClientAttrsSerializer(RemoteAppAttrsSerializer):
    REMOTE_APP_PATH = 'C:\Program Files (x86)\VMware\Infrastructure\Virtual Infrastructure Client\Launcher\VpxClient.exe'
    path = serializers.CharField(max_length=128, label=_('Application path'), default=REMOTE_APP_PATH)
    vmware_target = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Target URL'))
    vmware_username = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Username'))
    vmware_password = serializers.CharField(max_length=128, allow_blank=True, required=False, write_only=True, label=_('Password'))


class CustomRemoteAppAttrsSeralizers(RemoteAppAttrsSerializer):
    custom_cmdline = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Operating parameter'))
    custom_target = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Target url'))
    custom_username = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('Username'))
    custom_password = serializers.CharField(max_length=128, allow_blank=True, required=False, write_only=True, label=_('Password'))


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
    def get_parameters(obj):
        """
        返回Guacamole需要的RemoteApp配置参数信息中的parameters参数
        """
        serializer_cls = Category.get_type_serializer_cls(obj.type)
        fields = serializer_cls().get_fields()
        fields.pop('asset', None)
        fields_name = list(fields.keys())
        attrs = obj.attrs
        _parameters = list()
        _parameters.append(obj.type)
        for field_name in list(fields_name):
            value = attrs.get(field_name, None)
            if not value:
                continue
            if field_name == 'path':
                value = '\"%s\"' % value
            _parameters.append(str(value))
        _parameters = ' '.join(_parameters)
        return _parameters

    def get_parameter_remote_app(self, obj):
        parameters = self.get_parameters(obj)
        parameter = {
            'program': const.REMOTE_APP_BOOT_PROGRAM_NAME,
            'working_directory': '',
            'parameters': parameters,
        }
        return parameter

    @staticmethod
    def get_asset(obj):
        return obj.attrs.get('asset')


# TODO: DELETE
class RemoteAppParamsDictField(CustomMetaDictField):
    type_fields_map = const.REMOTE_APP_TYPE_FIELDS_MAP
    default_type = const.REMOTE_APP_TYPE_CHROME
    convert_key_remove_type_prefix = False
    convert_key_to_upper = False


# TODO: DELETE
class RemoteAppSerializer(BulkOrgResourceModelSerializer):
    params = RemoteAppParamsDictField(label=_('Parameters'))
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
        extra_kwargs = {
            'asset_info': {'label': _('Asset info')},
            'get_type_display': {'label': _('Type for display')},
        }

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


