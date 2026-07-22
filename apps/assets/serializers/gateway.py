# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import Account
from common.serializers import CommonModelSerializer
from .asset.host import HostSerializer
from ..models import Gateway, Asset

__all__ = ['GatewaySerializer', 'GatewayWithAccountSerializer']


class GatewaySerializer(HostSerializer):
    class Meta(HostSerializer.Meta):
        model = Gateway

    def validate_platform(self, p):
        if not p.name.startswith('Gateway'):
            raise serializers.ValidationError(_('The platform must start with Gateway'))
        return p

    def validate_name(self, value):
        queryset = Asset.objects.filter(name=value)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        has = queryset.exists()
        if has:
            raise serializers.ValidationError(_('This field must be unique.'))
        return value


class GatewayAccountSerializer(CommonModelSerializer):
    """Gateway 关联账号的非敏感元数据

    仅暴露 ``name``/``username``/``privileged``/``secret_type``，
    刻意不包含 ``secret``/``private_key``/``password`` 等可恢复凭据的字段，
    避免 Zone/Database 等普通查询接口泄露账号明文凭据。
    合法门禁的凭据下发应走 ConnectionToken 等专用链路。
    """

    class Meta:
        model = Account
        fields = ['name', 'username', 'privileged', 'secret_type']


class GatewayWithAccountSerializer(GatewaySerializer):
    account = GatewayAccountSerializer(
        required=False, label=_('Account'), source='select_account'
    )

    class Meta(GatewaySerializer.Meta):
        fields = GatewaySerializer.Meta.fields + ['account']
