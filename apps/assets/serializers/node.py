# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Asset, Node

__all__ = [
    'NodeSerializer', "NodeAddChildrenSerializer",
    "NodeAssetsSerializer", "NodeAssetsAmountQuerySerializer",
    "NodeAssetTreeSearchQuerySerializer", "NodeTreeMetricsQuerySerializer",
    "NodeTreeAssetsLimitQuerySerializer", "NodeTreeAssetsOrderQuerySerializer",
    "NodeTaskSerializer",
]


class NodeSerializer(BulkOrgResourceModelSerializer):
    name = serializers.ReadOnlyField(source='value')
    assets_amount = serializers.SerializerMethodField(
        label=_("Assets amount")
    )
    value = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, label=_("value")
    )
    full_value = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, label=_("Full value")
    )

    class Meta:
        model = Node
        only_fields = ['id', 'key', 'value', 'org_id']
        fields = only_fields + ['name', 'full_value', 'assets_amount']
        read_only_fields = ['key', 'org_id']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.method != 'GET':
            fields.pop('assets_amount', None)
        return fields

    @staticmethod
    def get_assets_amount(obj):
        amount = getattr(obj, 'assets_amount_realtime', None)
        if amount is not None:
            return amount
        return obj.get_assets_amount()

    def validate_value(self, data):
        if '/' in data:
            error = _("Can't contains: " + "/")
            raise serializers.ValidationError(error)
        view = self.context['view']
        instance = self.instance or getattr(view, 'instance', None)
        if instance:
            siblings = instance.get_siblings()
        else:
            instance = Node.org_root()
            siblings = instance.get_children()
        if siblings.filter(value=data):
            raise serializers.ValidationError(
                _('The same level node name cannot be the same')
            )
        return data

    def create(self, validated_data):
        full_value = validated_data.get('full_value')

        # 直接多层级创建
        if full_value:
            node = Node.create_node_by_full_value(full_value)
        # 根据 value 在 root 下创建
        else:
            key = Node.org_root().get_next_child_key()
            validated_data['key'] = key
            node = Node.objects.create(**validated_data)
        return node


class NodeAssetsSerializer(BulkOrgResourceModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Asset.objects
    )

    class Meta:
        model = Node
        fields = ['assets']


class NodeAssetsAmountQuerySerializer(serializers.Serializer):
    node_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        max_length=200,
    )
    include_descendants = serializers.BooleanField(
        default=True,
        required=False,
    )
    fresh = serializers.BooleanField(default=False, required=False)

    @staticmethod
    def validate_node_ids(node_ids):
        # Preserve the requested order while preventing duplicate correlated
        # subqueries inside the same batch.
        return list(dict.fromkeys(node_ids))


class NodeAssetTreeSearchQuerySerializer(serializers.Serializer):
    search = serializers.CharField(max_length=256, trim_whitespace=True)
    target = serializers.ChoiceField(
        choices=('node', 'asset'), default='asset', required=False
    )
    node_id = serializers.UUIDField(required=False)
    limit = serializers.IntegerField(
        min_value=1, max_value=1000, default=1000, required=False
    )


class NodeTreeAssetsLimitQuerySerializer(serializers.Serializer):
    assets_limit = serializers.IntegerField(min_value=1, max_value=1000)


class NodeTreeAssetsOrderQuerySerializer(serializers.Serializer):
    asset_order = serializers.ChoiceField(
        choices=('name', 'address'), default='name', required=False
    )


class TreeMetricItemSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=('node', 'asset'))
    id = serializers.UUIDField()


class NodeTreeMetricsQuerySerializer(serializers.Serializer):
    METRIC_CHOICES = ('asset_all', 'asset_direct', 'search_assets')

    items = TreeMetricItemSerializer(
        many=True, allow_empty=False, max_length=200
    )
    metric = serializers.ChoiceField(choices=METRIC_CHOICES)
    search = serializers.CharField(
        required=False, allow_blank=True, max_length=256,
        trim_whitespace=True,
    )
    node_id = serializers.UUIDField(required=False)
    fresh = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs):
        if attrs['metric'] == 'search_assets' and not attrs.get('search'):
            raise serializers.ValidationError({
                'search': _('This field may not be blank.'),
            })

        seen = set()
        items = []
        for item in attrs['items']:
            identity = (item['type'], item['id'])
            if identity in seen:
                continue
            seen.add(identity)
            items.append(item)
        attrs['items'] = items
        return attrs


class NodeAddChildrenSerializer(serializers.Serializer):
    nodes = serializers.ListField()


class NodeTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('refresh', 'refresh'),
        ('test', 'test'),
        ('refresh_cache', 'refresh_cache'),
    )
    task = serializers.CharField(read_only=True)
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
