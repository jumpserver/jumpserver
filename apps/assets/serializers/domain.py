# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import SecretReadableMixin
from common.drf.fields import ObjectRelatedField
from ..serializers import HostSerializer
from ..models import Domain, Gateway, Asset


class DomainSerializer(BulkOrgResourceModelSerializer):
    asset_count = serializers.SerializerMethodField(label=_('Assets amount'))
    gateway_count = serializers.SerializerMethodField(label=_('Gateways count'))
    assets = ObjectRelatedField(
        many=True, required=False, queryset=Asset.objects, label=_('Asset')
    )

    class Meta:
        model = Domain
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['comment']
        fields_m2m = ['assets']
        read_only_fields = ['asset_count', 'gateway_count', 'date_created']
        fields = fields_small + fields_m2m + read_only_fields

        extra_kwargs = {
            'assets': {'required': False, 'label': _('Assets')},
        }

    @staticmethod
    def get_asset_count(obj):
        return obj.assets.count()

    @staticmethod
    def get_gateway_count(obj):
        return obj.gateways.count()


class GatewaySerializer(HostSerializer):
    effective_accounts = serializers.SerializerMethodField()

    class Meta(HostSerializer.Meta):
        model = Gateway
        fields = HostSerializer.Meta.fields + ['effective_accounts']

    @staticmethod
    def get_effective_accounts(obj):
        accounts = obj.select_accounts.values()
        return [
            {
                'id': account.id,
                'username': account.username,
                'secret_type': account.secret_type,
            } for account in accounts
        ]


class DomainWithGatewaySerializer(BulkOrgResourceModelSerializer):
    gateways = GatewaySerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
