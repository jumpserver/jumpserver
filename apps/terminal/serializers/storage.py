# -*- coding: utf-8 -*-
#
from urllib.parse import urlparse

from django.core.validators import MaxValueValidator, MinValueValidator, validate_ipv46_address
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from common.serializers.fields import EncryptedField
from common.storage.serializers import BaseStorageSerializer, StorageTypeESSerializer
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
        label=_('Access key ID'), allow_null=True,
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
        allow_blank=True, allow_null=True, required=False, max_length=1024, label=_('Passphrase')
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


class SaveHandleMixin(serializers.Serializer):
    def save(self, **kwargs):
        instance = super().save(**kwargs)
        if self.validated_data.get('is_default', False):
            instance.set_to_default()
        return instance


# Command storage serializers
# ---------------------------
class CommandStorageSerializer(SaveHandleMixin, BaseStorageSerializer):
    type = LabeledChoiceField(choices=const.CommandStorageType.choices, label=_('Type'))
    storage_type_serializer_classes_mapping = {
        const.CommandStorageType.es.value: StorageTypeESSerializer
    }

    class Meta(BaseStorageSerializer.Meta):
        model = CommandStorage


# ReplayStorageSerializer
class ReplayStorageSerializer(SaveHandleMixin, BaseStorageSerializer):
    type = LabeledChoiceField(choices=const.ReplayStorageType.choices, label=_('Type'))
    storage_type_serializer_classes_mapping = replay_storage_type_serializer_classes_mapping

    class Meta(BaseStorageSerializer.Meta):
        model = ReplayStorage

    def validate_is_default(self, value):
        if self.initial_data.get('type') == const.ReplayStorageType.sftp.value:
            # sftp不能设置为默认存储
            return False
        else:
            return value
