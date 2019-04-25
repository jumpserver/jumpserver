# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.serializers import AdaptedBulkListSerializer

from ..models import Domain, Gateway


class DomainSerializer(serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()
    gateway_count = serializers.SerializerMethodField()

    class Meta:
        model = Domain
        fields = '__all__'
        list_serializer_class = AdaptedBulkListSerializer

    @staticmethod
    def get_asset_count(obj):
        return obj.assets.count()

    @staticmethod
    def get_gateway_count(obj):
        return obj.gateway_set.all().count()


class GatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gateway
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'ip', 'port', 'protocol', 'username',
            'domain', 'is_active', 'date_created', 'date_updated',
            'created_by', 'comment',
        ]


class GatewayWithAuthSerializer(GatewaySerializer):
    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(
            ['password', 'private_key']
        )
        return fields


class DomainWithGatewaySerializer(serializers.ModelSerializer):
    gateways = GatewayWithAuthSerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
