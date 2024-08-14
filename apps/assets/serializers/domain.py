# -*- coding: utf-8 -*-
#
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models.gateway import Gateway
from common.serializers import ResourceLabelsMixin
from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .gateway import GatewayWithAccountSecretSerializer
from ..models import Domain

__all__ = ['DomainSerializer', 'DomainWithGatewaySerializer', 'DomainListSerializer']


class DomainSerializer(ResourceLabelsMixin, BulkOrgResourceModelSerializer):
    gateways = ObjectRelatedField(
        many=True, required=False, label=_('Gateway'), queryset=Gateway.objects,
        help_text=_(
            "A gateway is a network proxy for a zone, and when connecting assets within the zone, "
            "the connection is routed through the gateway.")
    )
    assets_amount = serializers.IntegerField(label=_('Assets amount'), read_only=True)

    class Meta:
        model = Domain
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['comment']
        fields_m2m = ['assets', 'gateways', 'assets_amount']
        read_only_fields = ['date_created']
        fields = fields_small + fields_m2m + read_only_fields
        extra_kwargs = {
            'assets': {'required': False, 'label': _('Assets')},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        assets = data.get('assets')
        if assets is None:
            return data
        gateway_ids = [str(i['id']) for i in data['gateways']]
        data['assets'] = [i for i in assets if str(i['id']) not in gateway_ids]
        return data

    def create(self, validated_data):
        assets = validated_data.pop('assets', [])
        gateways = validated_data.pop('gateways', [])
        validated_data['assets'] = assets + gateways
        return super().create(validated_data)

    def update(self, instance, validated_data):
        assets = validated_data.pop('assets', list(instance.assets.all()))
        gateways = validated_data.pop('gateways', list(instance.gateways.all()))
        validated_data['assets'] = assets + gateways
        return super().update(instance, validated_data)

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.prefetch_related('labels', 'labels__label')
        return queryset


class DomainListSerializer(DomainSerializer):
    class Meta(DomainSerializer.Meta):
        fields = list(set(DomainSerializer.Meta.fields + ['assets_amount']) - {'assets'})

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.annotate(
            assets_amount=Count('assets', filter=~Q(assets__platform__name='Gateway'), distinct=True),
        )
        return queryset


class DomainWithGatewaySerializer(serializers.ModelSerializer):
    gateways = GatewayWithAccountSecretSerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
