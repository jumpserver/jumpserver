# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from .asset.common import AccountSecretSerializer
from ..serializers import HostSerializer
from ..models import Gateway

__all__ = ['GatewaySerializer', 'GatewayWithAccountSecretSerializer']


class GatewaySerializer(HostSerializer):
    class Meta(HostSerializer.Meta):
        model = Gateway


class GatewayWithAccountSecretSerializer(GatewaySerializer):
    accounts = AccountSecretSerializer(many=True, required=False, label=_('Account'))

    class Meta(GatewaySerializer.Meta):
        fields = GatewaySerializer.Meta.fields + ['accounts']
