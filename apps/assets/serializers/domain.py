# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.fields import ObjectRelatedField
from ..serializers import GatewaySerializer
from ..models import Domain, Asset


__all__ = ['DomainSerializer', 'DomainWithGatewaySerializer']


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


class DomainWithGatewaySerializer(BulkOrgResourceModelSerializer):
    gateways = GatewaySerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
