# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from ..models import Node, AdminUser
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializer, AuthSerializerMixin


class AdminUserSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    """
    管理用户
    """

    class Meta:
        model = AdminUser
        fields_mini  = ['id', 'name', 'username']
        fields_write_only = ['password', 'private_key', 'public_key']
        fields_small = fields_mini + fields_write_only + [
            'date_created', 'date_updated',
            'comment', 'created_by'
        ]
        fields_fk = ['assets_amount']
        fields = fields_small + fields_fk
        read_only_fields = ['date_created', 'date_updated', 'created_by', 'assets_amount']

        extra_kwargs = {
            'username': {"required": True},
            'password': {"write_only": True},
            'private_key': {"write_only": True},
            'public_key': {"write_only": True},
            'assets_amount': {'label': _('Asset')},
        }


class AdminUserDetailSerializer(AdminUserSerializer):
    class Meta(AdminUserSerializer.Meta):
        fields = AdminUserSerializer.Meta.fields + ['ssh_key_fingerprint']


class AdminUserAuthSerializer(AuthSerializer):

    class Meta:
        model = AdminUser
        fields = ['password', 'private_key']


class ReplaceNodeAdminUserSerializer(serializers.ModelSerializer):
    """
    管理用户更新关联到的集群
    """
    nodes = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Node.objects
    )

    class Meta:
        model = AdminUser
        fields = ['id', 'nodes']


class TaskIDSerializer(serializers.Serializer):
    task = serializers.CharField(read_only=True)


class AssetUserTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('test', 'test'),
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    task = serializers.CharField(read_only=True)
