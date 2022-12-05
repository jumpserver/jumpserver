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
    gateways = ObjectRelatedField(
        many=True, required=False, queryset=Asset.objects, label=_('Gateway')
    )
    assets = ObjectRelatedField(
        many=True, required=False, queryset=Asset.objects, label=_('Asset')
    )

    class Meta:
        model = Domain
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['comment']
        fields_m2m = ['assets', 'gateways']
        read_only_fields = ['date_created']
        fields = fields_small + fields_m2m + read_only_fields
        extra_kwargs = {}


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


class DomainWithGatewaySerializer(BulkOrgResourceModelSerializer):
    gateways = GatewaySerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
