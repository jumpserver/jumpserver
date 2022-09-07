# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.transaction import atomic
from django.db.models import F

from common.drf.serializers import JMSWritableNestedModelSerializer
from common.drf.fields import LabeledChoiceField, ObjectRelatedField
from ..account import AccountSerializer
from ...models import Asset, Node, Platform, Protocol, Label, Domain, Account
from ...const import Category, AllTypes

__all__ = [
    'AssetSerializer', 'AssetSimpleSerializer', 'MiniAssetSerializer',
    'AssetTaskSerializer', 'AssetsTaskSerializer',
]


class AssetProtocolsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocol
        fields = ['id', 'name', 'port']

    def create(self, validated_data):
        instance = Protocol.objects.filter(**validated_data).first()
        if instance:
            return instance
        instance = Protocol.objects.create(**validated_data)
        return instance


class AssetLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['name', 'value']
        extra_kwargs = {
            'name': {'required': False},
            'value': {'required': False}
        }


class AssetPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ['id', 'name']
        extra_kwargs = {
            'name': {'required': False}
        }


class AssetSerializer(JMSWritableNestedModelSerializer):
    category = LabeledChoiceField(choices=Category.choices, read_only=True, label=_('Category'))
    type = LabeledChoiceField(choices=AllTypes.choices, read_only=True, label=_('Type'))
    domain = ObjectRelatedField(required=False, queryset=Domain.objects, label=_('Domain'))
    platform = ObjectRelatedField(required=False, queryset=Platform.objects, label=_('Platform'))
    nodes = ObjectRelatedField(many=True, required=False, queryset=Node.objects, label=_('Nodes'))
    labels = AssetLabelSerializer(many=True, required=False, label=_('Labels'))
    accounts = AccountSerializer(many=True, required=False, label=_('Accounts'))
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))
    """
    资产的数据结构
    """
    class Meta:
        model = Asset
        fields_mini = [
            'id', 'name', 'ip',
        ]
        fields_small = fields_mini + [
            'is_active', 'comment',
        ]
        fields_fk = [
            'domain', 'platform', 'platform',
        ]
        fields_m2m = [
            'nodes', 'labels', 'accounts', 'protocols', 'nodes_display',
        ]
        read_only_fields = [
            'category', 'type', 'connectivity', 'date_verified',
            'created_by', 'date_created',
        ]
        fields = fields_small + fields_fk + fields_m2m + read_only_fields
        extra_kwargs = {
            'name': {'label': _("Name")},
            'ip': {'label': _('IP/Host')},
            'protocol': {'write_only': True},
            'port': {'write_only': True},
            'admin_user_display': {'label': _('Admin user display'), 'read_only': True},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('domain', 'platform', 'protocols') \
            .annotate(category=F("platform__category")) \
            .annotate(type=F("platform__type"))
        queryset = queryset.prefetch_related('nodes', 'labels')
        return queryset

    def perform_nodes_display_create(self, instance, nodes_display):
        if not nodes_display:
            return
        nodes_to_set = []
        for full_value in nodes_display:
            node = Node.objects.filter(full_value=full_value).first()
            if node:
                nodes_to_set.append(node)
            else:
                node = Node.create_node_by_full_value(full_value)
            nodes_to_set.append(node)
        instance.nodes.set(nodes_to_set)

    @atomic
    def create(self, validated_data):
        nodes_display = validated_data.pop('nodes_display', '')
        instance = super().create(validated_data)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance

    @atomic
    def update(self, instance, validated_data):
        nodes_display = validated_data.pop('nodes_display', '')
        instance = super().update(instance, validated_data)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance


class MiniAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = AssetSerializer.Meta.fields_mini


class AssetSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'id', 'name', 'ip', 'port',
            'connectivity', 'date_verified'
        ]


class AssetsTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('refresh', 'refresh'),
        ('test', 'test'),
    )
    task = serializers.CharField(read_only=True)
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    assets = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects, required=False, allow_empty=True, many=True
    )


class AssetTaskSerializer(AssetsTaskSerializer):
    ACTION_CHOICES = tuple(list(AssetsTaskSerializer.ACTION_CHOICES) + [
        ('push_system_user', 'push_system_user'),
        ('test_system_user', 'test_system_user')
    ])
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    asset = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects, required=False, allow_empty=True, many=False
    )
