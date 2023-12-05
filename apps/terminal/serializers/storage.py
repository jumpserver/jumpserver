# -*- coding: utf-8 -*-
#
from urllib.parse import urlparse

from django.db.models import TextChoices
from django.core.validators import MaxValueValidator, MinValueValidator, validate_ipv46_address
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from common.serializers import MethodSerializer
from common.serializers.fields import LabeledChoiceField
from common.serializers.fields import ReadableHiddenField, EncryptedField
from .. import const
from ..models import ReplayStorage, CommandStorage


# Replay storage serializers
# --------------------------
def replay_storage_endpoint_format_validator(endpoint):
    h = urlparse(endpoint)
    if h.path:
        raise serializers.ValidationError(_('Endpoint invalid: remove path `{}`').format(h.path))
    return endpoint


class ReplayStorageTypeBaseSerializer(serializers.Serializer):
    BUCKET = serializers.CharField(
        required=True, max_length=1024, label=_('Bucket'), allow_null=True
    )
    ACCESS_KEY = serializers.CharField(
        max_length=1024, required=False, allow_blank=True,
        label=_('Access key id'), allow_null=True,
    )
    SECRET_KEY = EncryptedField(
        max_length=1024, required=False, allow_blank=True,
        label=_('Access key secret'), allow_null=True,
    )
    ENDPOINT = serializers.CharField(
        validators=[replay_storage_endpoint_format_validator],
        required=True, max_length=1024, label=_('Endpoint'), allow_null=True,
    )


class ReplayStorageTypeS3Serializer(ReplayStorageTypeBaseSerializer):
    endpoint_help_text = '''
        S3 format: http://s3.{REGION_NAME}.amazonaws.com <br>
        S3(China) format: http://s3.{REGION_NAME}.amazonaws.com.cn <br>
        Such as: http://s3.cn-north-1.amazonaws.com.cn
    '''
    ENDPOINT = serializers.CharField(
        validators=[replay_storage_endpoint_format_validator],
        required=True, max_length=1024, label=_('Endpoint'), help_text=_(endpoint_help_text),
        allow_null=True,
    )


class ReplayStorageTypeCephSerializer(ReplayStorageTypeBaseSerializer):
    pass


class ReplayStorageTypeSwiftSerializer(ReplayStorageTypeBaseSerializer):
    class ProtocolChoices(TextChoices):
        http = 'http', 'http'
        https = 'https', 'https'

    REGION = serializers.CharField(
        required=True, max_length=1024, label=_('Region'), allow_null=True
    )
    PROTOCOL = serializers.ChoiceField(
        choices=ProtocolChoices.choices, default=ProtocolChoices.http.value, label=_('Protocol'),
        allow_null=True,
    )


class ReplayStorageTypeOSSSerializer(ReplayStorageTypeBaseSerializer):
    endpoint_help_text = '''
        OSS format: http://{REGION_NAME}.aliyuncs.com <br>
        Such as: http://oss-cn-hangzhou.aliyuncs.com
    '''
    ENDPOINT = serializers.CharField(
        validators=[replay_storage_endpoint_format_validator],
        max_length=1024, label=_('Endpoint'), help_text=_(endpoint_help_text), allow_null=True,
    )


class ReplayStorageTypeOBSSerializer(ReplayStorageTypeBaseSerializer):
    endpoint_help_text = '''
        OBS format: obs.{REGION_NAME}.myhuaweicloud.com <br>
        Such as: obs.cn-north-4.myhuaweicloud.com
    '''
    ENDPOINT = serializers.CharField(
        max_length=1024, label=_('Endpoint'), help_text=_(endpoint_help_text), allow_null=True,
    )


class ReplayStorageTypeCOSSerializer(ReplayStorageTypeS3Serializer):
    endpoint_help_text = '''Such as: http://cos.{REGION_NAME}.myqcloud.com'''
    ENDPOINT = serializers.CharField(
        validators=[replay_storage_endpoint_format_validator],
        required=True, max_length=1024, label=_('Endpoint'), help_text=_(endpoint_help_text),
        allow_null=True,
    )


class ReplayStorageTypeAzureSerializer(serializers.Serializer):
    class EndpointSuffixChoices(TextChoices):
        china = 'core.chinacloudapi.cn', 'core.chinacloudapi.cn'
        international = 'core.windows.net', 'core.windows.net'

    CONTAINER_NAME = serializers.CharField(
        max_length=1024, label=_('Container name'), allow_null=True
    )
    ACCOUNT_NAME = serializers.CharField(max_length=1024, label=_('Account name'), allow_null=True)
    ACCOUNT_KEY = EncryptedField(max_length=1024, label=_('Account key'), allow_null=True)
    ENDPOINT_SUFFIX = serializers.ChoiceField(
        choices=EndpointSuffixChoices.choices, default=EndpointSuffixChoices.china.value,
        label=_('Endpoint suffix'), allow_null=True,
    )


class SftpSecretType(TextChoices):
    PASSWORD = 'password', _('Password')
    SSH_KEY = 'ssh_key', _('SSH key')


class ReplayStorageTypeSFTPSerializer(serializers.Serializer):
    SFTP_HOST = serializers.CharField(
        required=True, max_length=1024, label=_('HOST'), validators=[validate_ipv46_address]
    )
    SFTP_PORT = serializers.IntegerField(
        required=False, default=22, validators=[MaxValueValidator(65535), MinValueValidator(0)],
        label=_('Port')
    )
    SFTP_USERNAME = serializers.CharField(
        required=True, max_length=1024, label=_('Username')
    )
    STP_SECRET_TYPE = serializers.ChoiceField(choices=SftpSecretType.choices,
                                              default=SftpSecretType.PASSWORD,
                                              label=_('Secret type'))
    SFTP_PASSWORD = EncryptedField(
        allow_blank=True, allow_null=True, required=False, max_length=1024, label=_('Password')
    )
    STP_PRIVATE_KEY = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, max_length=4096,
        write_only=True, label=_('Private key')
    )
    STP_PASSPHRASE = EncryptedField(
        allow_blank=True, allow_null=True, required=False, max_length=1024, label=_('Key password')
    )
    SFTP_ROOT_PATH = serializers.CharField(
        required=True, max_length=1024, label=_('SFTP Root')
    )


# mapping
replay_storage_type_serializer_classes_mapping = {
    const.ReplayStorageType.s3.value: ReplayStorageTypeS3Serializer,
    const.ReplayStorageType.ceph.value: ReplayStorageTypeCephSerializer,
    const.ReplayStorageType.swift.value: ReplayStorageTypeSwiftSerializer,
    const.ReplayStorageType.oss.value: ReplayStorageTypeOSSSerializer,
    const.ReplayStorageType.azure.value: ReplayStorageTypeAzureSerializer,
    const.ReplayStorageType.obs.value: ReplayStorageTypeOBSSerializer,
    const.ReplayStorageType.cos.value: ReplayStorageTypeCOSSerializer,
    const.ReplayStorageType.sftp.value: ReplayStorageTypeSFTPSerializer
}


# Command storage serializers
# ---------------------------
def command_storage_es_host_format_validator(host):
    if '#' in host:
        raise serializers.ValidationError(_('The address cannot contain the special character `#`'))
    h = urlparse(host)
    default_error_msg = _('The address format is incorrect')
    if h.scheme not in ['http', 'https']:
        raise serializers.ValidationError(default_error_msg)
    if ':' not in h.netloc:
        raise serializers.ValidationError(default_error_msg)
    _host, _port = h.netloc.rsplit(':', maxsplit=1)
    if not _host:
        error_msg = _('Host invalid')
        raise serializers.ValidationError(error_msg)
    if not _port.isdigit():
        error_msg = _('Port invalid')
        raise serializers.ValidationError(error_msg)
    return host


class CommandStorageTypeESSerializer(serializers.Serializer):
    hosts_help_text = '''
        Tip: If there are multiple hosts, use a comma (,) to separate them. <br>
        (eg: http://www.jumpserver.a.com:9100, http://www.jumpserver.b.com:9100)
    '''
    HOSTS = serializers.ListField(
        child=serializers.CharField(validators=[command_storage_es_host_format_validator]),
        label=_('Hosts'), help_text=_(hosts_help_text), allow_null=True
    )
    INDEX_BY_DATE = serializers.BooleanField(
        default=False, label=_('Index by date'),
        help_text=_('Whether to create an index by date')
    )
    INDEX = serializers.CharField(
        max_length=1024, default='jumpserver', label=_('Index'), allow_null=True
    )
    DOC_TYPE = ReadableHiddenField(default='_doc', label=_('Doc type'), allow_null=True)
    IGNORE_VERIFY_CERTS = serializers.BooleanField(
        default=False, label=_('Ignore Certificate Verification'),
        source='OTHER.IGNORE_VERIFY_CERTS', allow_null=True,
    )


# mapping
command_storage_type_serializer_classes_mapping = {
    const.CommandStorageType.es.value: CommandStorageTypeESSerializer
}


# BaseStorageSerializer
class BaseStorageSerializer(serializers.ModelSerializer):
    storage_type_serializer_classes_mapping = {}
    meta = MethodSerializer()

    class Meta:
        model = None
        fields = ['id', 'name', 'type', 'meta', 'is_default', 'comment']

    def validate_meta(self, meta):
        _meta = self.instance.meta if self.instance else {}
        _meta.update(meta)
        return _meta

    def get_meta_serializer(self):
        default_serializer = serializers.Serializer(read_only=True)

        if isinstance(self.instance, self.__class__.Meta.model):
            _type = self.instance.type
        else:
            _type = self.context['request'].query_params.get('type')

        if _type:
            serializer_class = self.storage_type_serializer_classes_mapping.get(_type)
        else:
            serializer_class = default_serializer

        if not serializer_class:
            serializer_class = default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class
        return serializer

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        if self.validated_data.get('is_default', False):
            instance.set_to_default()
        return instance


# CommandStorageSerializer
class CommandStorageSerializer(BaseStorageSerializer):
    type = LabeledChoiceField(choices=const.CommandStorageType.choices, label=_('Type'))
    storage_type_serializer_classes_mapping = command_storage_type_serializer_classes_mapping

    class Meta(BaseStorageSerializer.Meta):
        model = CommandStorage
        extra_kwargs = {
            'name': {'validators': [UniqueValidator(queryset=CommandStorage.objects.all())]}
        }


# ReplayStorageSerializer
class ReplayStorageSerializer(BaseStorageSerializer):
    type = LabeledChoiceField(choices=const.ReplayStorageType.choices, label=_('Type'))
    storage_type_serializer_classes_mapping = replay_storage_type_serializer_classes_mapping

    class Meta(BaseStorageSerializer.Meta):
        model = ReplayStorage
        extra_kwargs = {
            'name': {'validators': [UniqueValidator(queryset=ReplayStorage.objects.all())]}
        }

    def validate_is_default(self, value):
        if self.initial_data.get('type') == const.ReplayStorageType.sftp.value:
            # sftp不能设置为默认存储
            return False
        else:
            return value
