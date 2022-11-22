# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import SecretReadableMixin
from ..models import Domain, Asset


class DomainSerializer(BulkOrgResourceModelSerializer):
    asset_count = serializers.SerializerMethodField(label=_('Assets amount'))
    gateway_count = serializers.SerializerMethodField(label=_('Gateways count'))

    class Meta:
        model = Domain
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'comment', 'date_created'
        ]
        fields_m2m = [
            'asset_count', 'assets', 'gateway_count',
        ]
        fields = fields_small + fields_m2m
        read_only_fields = ('asset_count', 'gateway_count', 'date_created')
        extra_kwargs = {
            'assets': {'required': False, 'label': _('Assets')},
        }

    @staticmethod
    def get_asset_count(obj):
        return obj.assets.count()

    @staticmethod
    def get_gateway_count(obj):
        return obj.gateways.count()


class GatewaySerializer(BulkOrgResourceModelSerializer):
    is_connective = serializers.BooleanField(required=False, label=_('Connectivity'))

    class Meta:
        model = Asset
        fields_mini = ['id']
        fields_small = fields_mini + [
            'address', 'port', 'protocol',
            'is_active', 'is_connective',
            'date_created', 'date_updated',
            'created_by', 'comment',
        ]
        fields_fk = ['domain']
        fields = fields_small + fields_fk


class GatewayWithAuthSerializer(SecretReadableMixin, GatewaySerializer):
    class Meta(GatewaySerializer.Meta):
        extra_kwargs = {
            'password': {'write_only': False},
            'private_key': {"write_only": False},
            'public_key': {"write_only": False},
        }


class DomainWithGatewaySerializer(BulkOrgResourceModelSerializer):
    gateways = GatewayWithAuthSerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
