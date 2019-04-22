# -*- coding: utf-8 -*-
#

import uuid

from rest_framework import serializers
from rest_framework_bulk.serializers import BulkListSerializer

from common.utils import get_object_or_none
from common.mixins import BulkSerializerMixin
from ..models import Asset, Domain, AdminUser, Node
from .system_user import AssetSystemUserSerializer

__all__ = [
    'AssetSerializer', 'AssetGrantedSerializer', 'MyAssetGrantedSerializer',
    'AssetAsNodeSerializer', 'AssetSimpleSerializer',
    'AssetImportTemplateSerializer',
]


class AssetSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    """
    资产的数据结构
    """
    class Meta:
        model = Asset
        list_serializer_class = BulkListSerializer
        fields = '__all__'
        validators = []

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('labels', 'nodes')\
            .select_related('admin_user')
        return queryset

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend([
            'hardware_info', 'connectivity', 'org_name'
        ])
        return fields


class AssetAsNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'hostname', 'ip', 'port', 'platform', 'protocol']


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
            "id", "hostname", "ip", "port", "system_users_granted",
            "is_active", "system_users_join", "os", 'domain',
            "platform", "comment", "protocol", "org_id", "org_name",
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


class AssetImportTemplateSerializer(BulkSerializerMixin,
                                    serializers.ModelSerializer
                                    ):
    admin_user = serializers.CharField(required=False, allow_blank=True)
    ip = serializers.IPAddressField(max_length=32, required=True)
    hostname = serializers.CharField(max_length=128, required=True)
    protocol = serializers.CharField(required=False, allow_blank=True)
    port = serializers.CharField(required=False, allow_blank=True)
    platform = serializers.CharField(required=False, allow_blank=True)
    domain = serializers.CharField(required=False, allow_blank=True)
    public_ip = serializers.IPAddressField(required=False, allow_blank=True)
    is_active = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        for k, v in validated_data.items():
            str(v).strip()
            if k == 'protocol':
                v = 'ssh' if v == '' else v
            elif k == 'port':
                v = 22 if v == '' else int(v)
            elif k == 'platform':
                v = 'Linux' if v == '' else v.lower().capitalize()
            elif k == 'domain':
                v = get_object_or_none(Domain, name=v)
            elif k == 'is_active':
                v = False if v in ['False', 0, 'false'] else True
            elif k == 'admin_user':
                v = get_object_or_none(AdminUser, name=v)
            if v != '':
                validated_data[k] = v

        node_id = self.context['request'].query_params.get('node_id', '')
        node = get_object_or_none(Node, id=node_id) if node_id else Node.root()
        validated_data['nodes'] = [node]

        return super().create(validated_data)

    class Meta:
        model = Asset
        list_serializer_class = BulkListSerializer
        fields = [
            'ip', 'hostname', 'protocol', 'port', 'platform', 'domain',
            'is_active', 'admin_user', 'public_ip'
        ]