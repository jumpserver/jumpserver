# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from rest_framework.validators import ValidationError

from django.utils.translation import ugettext_lazy as _

from orgs.mixins import OrgResourceSerializerMixin
from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from ..models import Asset, Protocol
from .system_user import AssetSystemUserSerializer

__all__ = [
    'AssetSerializer', 'AssetGrantedSerializer', 'MyAssetGrantedSerializer',
    'AssetAsNodeSerializer', 'AssetSimpleSerializer',
]


class ProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocol
        fields = ["name", "port"]


class AssetSerializer(BulkSerializerMixin, OrgResourceSerializerMixin,
                      serializers.ModelSerializer):
    protocols = ProtocolSerializer(many=True)

    """
    资产的数据结构
    """
    class Meta:
        model = Asset
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'org_id', 'org_name', 'ip', 'hostname', 'protocol', 'port',
            'protocols', 'platform', 'is_active', 'public_ip', 'domain',
            'admin_user', 'nodes', 'labels', 'number', 'vendor', 'model', 'sn',
            'cpu_model', 'cpu_count', 'cpu_cores', 'cpu_vcpus', 'memory',
            'disk_total', 'disk_info', 'os', 'os_version', 'os_arch',
            'hostname_raw', 'comment', 'created_by', 'date_created',
            'hardware_info', 'connectivity'
        ]
        read_only_fields = (
            'vendor', 'model', 'sn', 'cpu_model', 'cpu_count',
            'cpu_cores', 'cpu_vcpus', 'memory', 'disk_total', 'disk_info',
            'os', 'os_version', 'os_arch', 'hostname_raw',
            'created_by', 'date_created',
        )
        extra_kwargs = {
            'hardware_info': {'label': _('Hardware info')},
            'connectivity': {'label': _('Connectivity')},
            'org_name': {'label': _('Org name')}
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('labels', 'nodes')\
            .select_related('admin_user')
        return queryset

    @staticmethod
    def validate_protocols(attr):
        protocols_name = [i.get("name", "ssh") for i in attr]
        errors = [{} for i in protocols_name]
        for i, name in enumerate(protocols_name):
            if name in protocols_name[:i]:
                errors[i] = {"name": _("Protocol duplicate: {}").format(name)}
        if any(errors):
            raise ValidationError(errors)
        return attr

    def create(self, validated_data):
        protocols_data = validated_data.pop("protocols")

        # 兼容老的api
        protocol = validated_data.get("protocol")
        port = validated_data.get("port")
        if not protocols_data and protocol and port:
            protocols_data = [{"name": protocol, "port": port}]

        if not protocol and not port and protocols_data:
            validated_data["protocol"] = protocols_data[0]["name"]
            validated_data["port"] = protocols_data[0]["port"]

        protocols_serializer = ProtocolSerializer(data=protocols_data, many=True)
        protocols_serializer.is_valid(raise_exception=True)
        protocols = protocols_serializer.save()
        instance = super().create(validated_data)
        instance.protocols.set(protocols)
        return instance

    def update(self, instance, validated_data):
        protocols_data = validated_data.pop("protocols")

        # 兼容老的api
        protocol = validated_data.get("protocol")
        port = validated_data.get("port")
        if not protocols_data and protocol and port:
            protocols_data = [{"name": protocol, "port": port}]

        if not protocol and not port and protocols_data:
            validated_data["protocol"] = protocols_data[0]["name"]
            validated_data["port"] = protocols_data[0]["port"]

        protocols_serializer = ProtocolSerializer(data=protocols_data, many=True)
        protocols_serializer.is_valid(raise_exception=True)
        protocols = protocols_serializer.save()

        instance = super().update(instance, validated_data)
        instance.protocols.all().delete()
        instance.protocols.set(protocols)
        return instance


class AssetAsNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'hostname', 'ip', 'platform', 'protocols']


class AssetGrantedSerializer(serializers.ModelSerializer):
    """
    被授权资产的数据结构
    """
    system_users_granted = AssetSystemUserSerializer(many=True, read_only=True)
    system_users_join = serializers.SerializerMethodField()
    # nodes = NodeTMPSerializer(many=True, read_only=True)

    class Meta:
        model = Asset
        fields = (
            "id", "hostname", "ip", "system_users_granted",
            "is_active", "system_users_join", "os", 'domain',
            "platform", "comment", "protocols", "org_id", "org_name",
        )

    @staticmethod
    def get_system_users_join(obj):
        system_users = [s.username for s in obj.system_users_granted]
        return ', '.join(system_users)


class MyAssetGrantedSerializer(AssetGrantedSerializer):
    """
    普通用户获取授权的资产定义的数据结构
    """

    class Meta:
        model = Asset
        fields = (
            "id", "hostname", "system_users_granted",
            "is_active", "system_users_join", "org_name",
            "os", "platform", "comment", "org_id", "protocol"
        )


class AssetSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'hostname', 'port', 'ip', 'connectivity']
