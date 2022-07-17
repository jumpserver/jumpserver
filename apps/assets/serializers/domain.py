# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from common.validators import alphanumeric
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import SecretReadableMixin
from ..models import Domain, Gateway
from .base import AuthSerializerMixin


class DomainSerializer(BulkOrgResourceModelSerializer):
    asset_count = serializers.SerializerMethodField(label=_('Assets amount'))
    application_count = serializers.SerializerMethodField(label=_('Applications amount'))
    gateway_count = serializers.SerializerMethodField(label=_('Gateways count'))

    class Meta:
        model = Domain
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'comment', 'date_created'
        ]
        fields_m2m = [
            'asset_count', 'assets', 'application_count', 'gateway_count',
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
    def get_application_count(obj):
        return obj.applications.count()

    @staticmethod
    def get_gateway_count(obj):
        return obj.gateway_set.all().count()


class GatewaySerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    is_connective = serializers.BooleanField(required=False, label=_('Connectivity'))

    class Meta:
        model = Gateway
        fields_mini = ['id', 'name']
        fields_write_only = [
            'password', 'private_key', 'public_key', 'passphrase'
        ]
        fields_small = fields_mini + fields_write_only + [
            'username', 'ip', 'port', 'protocol',
            'is_active', 'is_connective',
            'date_created', 'date_updated',
            'created_by', 'comment',
        ]
        fields_fk = ['domain']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'username': {"validators": [alphanumeric]},
            'password': {'write_only': True},
            'private_key': {"write_only": True},
            'public_key': {"write_only": True},
        }


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
