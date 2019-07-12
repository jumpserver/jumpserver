# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from common.fields import StringManyToManyField
from orgs.mixins import BulkOrgResourceModelSerializer
from perms.models import AssetPermission, Action
from assets.models import Asset

__all__ = [
    'AssetPermissionCreateUpdateSerializer', 'AssetPermissionListSerializer',
    'AssetPermissionUpdateUserSerializer', 'AssetPermissionUpdateAssetSerializer',
    'ActionsField', 'AssetPermissionAssetsSerializer',
]


class ActionsField(serializers.MultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = Action.CHOICES
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        return Action.value_to_choices(value)

    def to_internal_value(self, data):
        if data is None:
            return data
        return Action.choices_to_value(data)


class ActionsDisplayField(ActionsField):
    def to_representation(self, value):
        values = super().to_representation(value)
        choices = dict(Action.CHOICES)
        return [choices.get(i) for i in values]


class AssetPermissionCreateUpdateSerializer(BulkOrgResourceModelSerializer):
    actions = ActionsField(required=False, allow_null=True)

    class Meta:
        model = AssetPermission
        exclude = ('created_by', 'date_created')


class AssetPermissionListSerializer(BulkOrgResourceModelSerializer):
    users = StringManyToManyField(many=True, read_only=True)
    user_groups = StringManyToManyField(many=True, read_only=True)
    assets = StringManyToManyField(many=True, read_only=True)
    nodes = StringManyToManyField(many=True, read_only=True)
    system_users = StringManyToManyField(many=True, read_only=True)
    actions = ActionsDisplayField()
    is_valid = serializers.BooleanField()
    is_expired = serializers.BooleanField()

    class Meta:
        model = AssetPermission
        fields = '__all__'


class AssetPermissionUpdateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'users']


class AssetPermissionUpdateAssetSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'assets']


class AssetPermissionAssetsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Asset
        only_fields = ['id', 'hostname', 'ip']
        fields = tuple(only_fields)
