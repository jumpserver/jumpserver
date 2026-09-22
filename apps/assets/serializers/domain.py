# -*- coding: utf-8 -*-
#
from ipaddress import ip_network

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers import ResourceLabelsMixin
from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Zone, Gateway

__all__ = ['ZoneSerializer', 'ZoneListSerializer', 'CIDRListField']


class CIDRListField(serializers.ListField):
    child = serializers.CharField(max_length=64)

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 100)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        if self.max_length is not None and len(values) > self.max_length:
            self.fail('max_length', max_length=self.max_length)
        networks = []
        for value in values:
            try:
                if '/' not in value:
                    raise ValueError
                network = str(ip_network(value, strict=False))
            except ValueError:
                raise serializers.ValidationError(_('Invalid CIDR: %s') % value)
            if network not in networks:
                networks.append(network)
        return networks


class ZoneSerializer(ResourceLabelsMixin, BulkOrgResourceModelSerializer):
    cidrs = CIDRListField(required=False, label=_('CIDR ranges'))
    gateways = ObjectRelatedField(
        many=True, required=False, label=_('Gateway'), queryset=Gateway.objects,
        help_text=_(
            "A gateway is a network proxy for a zone, and when connecting assets within the zone, "
            "the connection is routed through the gateway.")
    )
    assets_amount = serializers.IntegerField(label=_('Assets amount'), read_only=True)

    class Meta:
        model = Zone
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['comment', 'cidrs', 'auto_assign']
        relation_count_fields = {
            'assets_amount': {
                'relation': 'assets',
                'excludes': {'platform__name__startswith': 'Gateway'},
            },
        }
        amount_fields = list(relation_count_fields)
        fields_m2m = ['assets', 'gateways', 'labels'] + amount_fields
        read_only_fields = ['date_created']
        fields = fields_small + fields_m2m + read_only_fields
        extra_kwargs = {
            'assets': {'required': False, 'label': _('Assets')},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        auto_assign = attrs.get('auto_assign', getattr(self.instance, 'auto_assign', False))
        cidrs = attrs.get('cidrs', getattr(self.instance, 'cidrs', []))
        if auto_assign and not cidrs:
            raise serializers.ValidationError({
                'cidrs': _('At least one CIDR is required when auto assignment is enabled.')
            })
        return attrs

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


class ZoneListSerializer(ZoneSerializer):
    class Meta(ZoneSerializer.Meta):
        fields = list(set(ZoneSerializer.Meta.fields + ZoneSerializer.Meta.amount_fields) - {'assets'})
