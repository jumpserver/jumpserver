# -*- coding: utf-8 -*-
#
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.common import UniqueBulkListSerializer
from common.serializers.fields import ObjectRelatedField
from common.serializers.mixin import ResourceLabelsMixin
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from orgs.utils import current_org
from .. import utils
from ..models import User, UserGroup

__all__ = [
    'UserGroupSerializer', 'UserGroupListSerializer',
]


class UserGroupBulkListSerializer(UniqueBulkListSerializer):
    unique_field = 'name'

    def get_unique_keys(self, validated_data):
        instances = {}
        if self.instance is not None:
            instances = self.instance.in_bulk([item['id'] for item in validated_data])

        for item in validated_data:
            instance = instances.get(item.get('id'))
            name = item.get('name', getattr(instance, 'name', None))
            org_id = current_org.id
            if current_org.is_root():
                org_id = item.get('org_id', getattr(instance, 'org_id', ''))
            yield org_id, name


class UserGroupSerializer(ResourceLabelsMixin, BulkOrgResourceModelSerializer):
    users = ObjectRelatedField(
        required=False, many=True, queryset=User.objects,
        attrs=("id", "name", "is_service_account"), label=_('Users'),
    )

    class Meta:
        model = UserGroup
        list_serializer_class = UserGroupBulkListSerializer
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'comment', 'date_created', 'created_by'
        ]
        fields = fields_mini + fields_small + ['users', 'labels']
        extra_kwargs = {
            'created_by': {'label': _('Created by'), 'read_only': True},
            'id': {'label': _('ID')},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_fields_queryset()

    def set_fields_queryset(self):
        users_field = self.fields.get('users')
        if users_field:
            users_field.child_relation.queryset = utils.get_current_org_members()

    def validate_name_conflict(self, validated_data, instance=None):
        name = validated_data.get('name', getattr(instance, 'name', None))
        org_id = current_org.id
        if current_org.is_root():
            org_id = validated_data.get('org_id', getattr(instance, 'org_id', ''))
        queryset = UserGroup.objects.filter(org_id=org_id, name=name)
        if instance is not None:
            queryset = queryset.exclude(pk=instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                {'name': _('This field must be unique.')}, code='unique',
            )

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:
            # Leave the savepoint before querying for a concurrent name conflict.
            self.validate_name_conflict(validated_data)
            raise

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError:
            self.validate_name_conflict(validated_data, instance)
            raise


class UserGroupListSerializer(UserGroupSerializer):
    users_amount = serializers.IntegerField(label=_('Users amount'), read_only=True)

    class Meta(UserGroupSerializer.Meta):
        relation_count_fields = {
            'users_amount': {
                'relation': 'users',
                'related_filters': {'is_service_account': False},
            },
        }
        amount_fields = list(relation_count_fields)
        fields = list(set(UserGroupSerializer.Meta.fields + amount_fields) - {'users'})
        extra_kwargs = {
            **UserGroupSerializer.Meta.extra_kwargs,
        }
