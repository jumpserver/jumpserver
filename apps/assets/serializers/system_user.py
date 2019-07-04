from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _

from common.serializers import AdaptedBulkListSerializer
from orgs.mixins import BulkOrgResourceModelSerializer
from ..models import SystemUser
from .base import AuthSerializer


class SystemUserSerializer(BulkOrgResourceModelSerializer):
    """
    系统用户
    """

    class Meta:
        model = SystemUser
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'username', 'password', 'public_key', 'private_key',
            'login_mode', 'login_mode_display', 'priority', 'protocol',
            'auto_push', 'cmd_filters', 'sudo', 'shell', 'comment', 'nodes',
            'assets_amount', 'connectivity_amount'
        ]
        extra_kwargs = {
            'password': {"write_only": True},
            'public_key': {"write_only": True},
            'private_key': {"write_only": True},
            'assets_amount': {'label': _('Asset')},
            'connectivity_amount': {'label': _('Connectivity')},
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('cmd_filters', 'nodes')
        return queryset


class SystemUserAuthSerializer(AuthSerializer):
    """
    系统用户认证信息
    """

    class Meta:
        model = SystemUser
        fields = [
            "id", "name", "username", "protocol",
            "login_mode", "password", "private_key",
        ]



class SystemUserSimpleSerializer(serializers.ModelSerializer):
    """
    系统用户最基本信息的数据结构
    """
    class Meta:
        model = SystemUser
        fields = ('id', 'name', 'username')



