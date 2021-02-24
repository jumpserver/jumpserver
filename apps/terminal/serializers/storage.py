# -*- coding: utf-8 -*-
#
import copy
from rest_framework import serializers
from urllib.parse import urlparse
from django.utils.translation import ugettext_lazy as _
from django.db.models import TextChoices
from common.drf.serializers import MethodSerializer
from common.drf.fields import ReadableHiddenField
from ..models import ReplayStorage, CommandStorage
from .. import const


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
        max_length=1024, required=False, allow_blank=True, write_only=True, label=_('Access key'),
        allow_null=True,
    )
    SECRET_KEY = serializers.CharField(
        max_length=1024, required=False, allow_blank=True, write_only=True, label=_('Secret key'),
        allow_null=True,
    )
    ENDPOINT = serializers.CharField(
        validators=[replay_storage_endpoint_format_validator],
        required=True, max_length=1024, label=_('Endpoint'), allow_null=True,
    )


class ReplayStorageTypeS3Serializer(ReplayStorageTypeBaseSerializer):
    endpoint_help_text = '''
        S3 format: http://s3.{REGION_NAME}.amazonaws.com
        S3(China) format: http://s3.{REGION_NAME}.amazonaws.com.cn
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
        OSS format: http://{REGION_NAME}.aliyuncs.com
        Such as: http://oss-cn-hangzhou.aliyuncs.com
    '''
    ENDPOINT = serializers.CharField(
        validators=[replay_storage_endpoint_format_validator],
        max_length=1024, label=_('Endpoint'), help_text=_(endpoint_help_text), allow_null=True,
    )


class ReplayStorageTypeAzureSerializer(serializers.Serializer):
    class EndpointSuffixChoices(TextChoices):
        china = 'core.chinacloudapi.cn', 'core.chinacloudapi.cn'
        international = 'core.windows.net', 'core.windows.net'

    CONTAINER_NAME = serializers.CharField(
        max_length=1024, label=_('Container name'), allow_null=True
    )
    ACCOUNT_NAME = serializers.CharField(max_length=1024, label=_('Account name'), allow_null=True)
    ACCOUNT_KEY = serializers.CharField(max_length=1024, label=_('Account key'), allow_null=True)
    ENDPOINT_SUFFIX = serializers.ChoiceField(
        choices=EndpointSuffixChoices.choices, default=EndpointSuffixChoices.china.value,
        label=_('Endpoint suffix'), allow_null=True,
    )

# mapping


replay_storage_type_serializer_classes_mapping = {
    const.ReplayStorageTypeChoices.s3.value: ReplayStorageTypeS3Serializer,
    const.ReplayStorageTypeChoices.ceph.value: ReplayStorageTypeCephSerializer,
    const.ReplayStorageTypeChoices.swift.value: ReplayStorageTypeSwiftSerializer,
    const.ReplayStorageTypeChoices.oss.value: ReplayStorageTypeOSSSerializer,
    const.ReplayStorageTypeChoices.azure.value: ReplayStorageTypeAzureSerializer
}

# ReplayStorageSerializer


class ReplayStorageSerializer(serializers.ModelSerializer):
    meta = MethodSerializer()

    class Meta:
        model = ReplayStorage
        fields = ['id', 'name', 'type', 'meta', 'comment']

    def validate_meta(self, meta):
        _meta = self.instance.meta if self.instance else {}
        _meta.update(meta)
        return _meta

    def get_meta_serializer(self):
        default_serializer = serializers.Serializer(read_only=True)

        if isinstance(self.instance, ReplayStorage):
            _type = self.instance.type
        else:
            _type = self.context['request'].query_params.get('type')

        if _type:
            serializer_class = replay_storage_type_serializer_classes_mapping.get(_type)
        else:
            serializer_class = default_serializer

        if not serializer_class:
            serializer_class = default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class
        return serializer


# Command storage serializers
# ---------------------------


def command_storage_es_host_format_validator(host):
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
        Tip: If there are multiple hosts, use a comma (,) to separate them. 
        (eg: http://www.jumpserver.a.com:9100, http://www.jumpserver.b.com:9100)
    '''
    HOSTS = serializers.ListField(
        child=serializers.CharField(validators=[command_storage_es_host_format_validator]),
        label=_('Hosts'), help_text=_(hosts_help_text), allow_null=True
    )
    INDEX = serializers.CharField(
        max_length=1024, default='jumpserver', label=_('Index'), allow_null=True
    )
    DOC_TYPE = ReadableHiddenField(default='command', label=_('Doc type'), allow_null=True)


# mapping


command_storage_type_serializer_classes_mapping = {
    const.CommandStorageTypeChoices.es.value: CommandStorageTypeESSerializer
}

# CommandStorageSerializer


class CommandStorageSerializer(serializers.ModelSerializer):
    meta = MethodSerializer()

    class Meta:
        model = CommandStorage
        fields = ['id', 'name', 'type', 'meta', 'comment']

    def validate_meta(self, meta):
        _meta = self.instance.meta if self.instance else {}
        _meta.update(meta)
        return _meta

    def get_meta_serializer(self):
        default_serializer = serializers.Serializer(read_only=True)

        if isinstance(self.instance, CommandStorage):
            _type = self.instance.type
        else:
            _type = self.context['request'].query_params.get('type')

        if _type:
            serializer_class = command_storage_type_serializer_classes_mapping.get(_type)
        else:
            serializer_class = default_serializer

        if not serializer_class:
            serializer_class = default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class
        return serializer
