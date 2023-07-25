# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .asset.common import AccountSecretSerializer
from .asset.host import HostSerializer
from ..models import Gateway, Asset

__all__ = ['GatewaySerializer', 'GatewayWithAccountSecretSerializer']


class GatewaySerializer(HostSerializer):
    class Meta(HostSerializer.Meta):
        model = Gateway

    def validate_name(self, value):
        queryset = Asset.objects.filter(name=value)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        has = queryset.exists()
        if has:
            raise serializers.ValidationError(_('This field must be unique.'))
        return value


class GatewayWithAccountSecretSerializer(GatewaySerializer):
    account = AccountSecretSerializer(required=False, label=_('Account'), source='select_account')

    class Meta(GatewaySerializer.Meta):
        fields = GatewaySerializer.Meta.fields + ['account']
