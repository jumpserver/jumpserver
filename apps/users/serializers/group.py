# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.fields import StringManyToManyField
from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import User, UserGroup
from .. import utils


__all__ = [
    'UserGroupSerializer', 'UserGroupListSerializer',
    'UserGroupUpdateMemberSerializer'
]


class UserGroupSerializer(BulkOrgResourceModelSerializer):
    users = serializers.PrimaryKeyRelatedField(
        required=False, many=True, queryset=User.objects, label=_('User')
    )

    class Meta:
        model = UserGroup
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name',  'users', 'comment', 'date_created',
            'created_by',
        ]
        extra_kwargs = {
            'created_by': {'label': _('Created by'), 'read_only': True}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_fields_queryset()

    def set_fields_queryset(self):
        users_field = self.fields['users']
        users_field.child_relation.queryset = utils.get_current_org_members()

    def validate_users(self, users):
        for user in users:
            if user.is_super_auditor:
                msg = _('Auditors cannot be join in the user group')
                raise serializers.ValidationError(msg)
        return users


class UserGroupListSerializer(UserGroupSerializer):
    users = StringManyToManyField(many=True, read_only=True)


class UserGroupUpdateMemberSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects)

    class Meta:
        model = UserGroup
        fields = ['id', 'users']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_fields_queryset()

    def set_fields_queryset(self):
        users_field = self.fields['users']
        users_field.child_relation.queryset = utils.get_current_org_members()

