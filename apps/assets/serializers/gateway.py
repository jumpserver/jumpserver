# -*- coding: utf-8 -*-
#
from ..serializers import HostSerializer
from ..models import Gateway

__all__ = ['GatewaySerializer']


class GatewaySerializer(HostSerializer):
    class Meta(HostSerializer.Meta):
        model = Gateway
