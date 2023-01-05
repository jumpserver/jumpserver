# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from .asset.common import AccountSecretSerializer
from ..models import Gateway
from ..serializers import HostSerializer

__all__ = ['GatewaySerializer', 'GatewayWithAccountSecretSerializer']


class GatewaySerializer(HostSerializer):
    class Meta(HostSerializer.Meta):
        model = Gateway

    def get_field_names(self, declared_fields, info):
        names = super(GatewaySerializer, self).get_field_names(declared_fields, info)
        excludes = ['nodes', 'labels', 'nodes_display', 'info', 'platform']
        return [name for name in names if name not in excludes]


class GatewayWithAccountSecretSerializer(GatewaySerializer):
    accounts = AccountSecretSerializer(many=True, required=False, label=_('Account'))

    class Meta(GatewaySerializer.Meta):
        fields = GatewaySerializer.Meta.fields + ['accounts']
