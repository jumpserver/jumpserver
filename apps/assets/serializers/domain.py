# -*- coding: utf-8 -*-
#
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers import ResourceLabelsMixin
from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .gateway import GatewayWithAccountSecretSerializer
from ..models import Domain

__all__ = ['DomainSerializer', 'DomainWithGatewaySerializer', 'DomainListSerializer']


class DomainSerializer(ResourceLabelsMixin, BulkOrgResourceModelSerializer):
    gateways = ObjectRelatedField(
        many=True, required=False, label=_('Gateway'), read_only=True,
    )

    class Meta:
        model = Domain
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['comment']
        fields_m2m = ['assets', 'gateways']
        read_only_fields = ['date_created']
        fields = fields_small + fields_m2m + read_only_fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        assets = data.get('assets')
        if assets is None:
            return data
        gateway_ids = [str(i['id']) for i in data['gateways']]
        data['assets'] = [i for i in assets if str(i['id']) not in gateway_ids]
        return data

    def update(self, instance, validated_data):
        assets = validated_data.pop('assets', [])
        assets = assets + list(instance.gateways)
        validated_data['assets'] = assets
        instance = super().update(instance, validated_data)
        return instance

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset \
            .prefetch_related('labels', 'labels__label')
        return queryset


class DomainListSerializer(DomainSerializer):
    assets_amount = serializers.IntegerField(label=_('Assets amount'), read_only=True)

    class Meta(DomainSerializer.Meta):
        fields = list(set(DomainSerializer.Meta.fields + ['assets_amount']) - {'assets'})

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.annotate(
            assets_amount=Count('assets', distinct=True),
        )
        return queryset


class DomainWithGatewaySerializer(serializers.ModelSerializer):
    gateways = GatewayWithAccountSecretSerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
