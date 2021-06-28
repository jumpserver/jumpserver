# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from ..models import SystemUser
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializerMixin


class AdminUserSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    """
    管理用户
    """

    class Meta:
        model = SystemUser
        fields_mini = ['id', 'name', 'username']
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

    def create(self, validated_data):
        data = {k: v for k, v in validated_data.items()}
        data['type'] = SystemUser.Type.admin
        return super().create(data)