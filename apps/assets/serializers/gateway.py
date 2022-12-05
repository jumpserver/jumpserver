# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from ..serializers import HostSerializer
from ..models import Gateway

__all__ = ['GatewaySerializer']


class GatewaySerializer(HostSerializer):
    effective_accounts = serializers.SerializerMethodField()

    class Meta(HostSerializer.Meta):
        model = Gateway
        fields = HostSerializer.Meta.fields + ['effective_accounts']

    @staticmethod
    def get_effective_accounts(obj):
        accounts = obj.accounts.all()
        return [
            {
                'id': account.id,
                'username': account.username,
                'secret_type': account.secret_type,
            } for account in accounts
        ]
