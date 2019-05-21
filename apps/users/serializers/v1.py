# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from common.utils import get_signer, validate_ssh_public_key
from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from ..models import User, UserGroup

signer = get_signer()


class UserSerializer(BulkSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = User
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'username', 'email', 'groups', 'groups_display',
            'role', 'role_display',  'wechat', 'phone', 'otp_level',
            'comment', 'source', 'source_display', 'is_valid', 'is_expired',
            'is_active', 'created_by', 'is_first_login',
            'date_password_last_updated', 'date_expired', 'avatar_url',
        ]
        extra_kwargs = {
            'groups_display': {'label': _('Groups name')},
            'source_display': {'label': _('Source name')},
            'is_first_login': {'label': _('Is first login'), 'read_only': True},
            'role_display': {'label': _('Role name')},
            'is_valid': {'label': _('Is valid')},
            'is_expired': {'label': _('Is expired')},
            'avatar_url': {'label': _('Avatar url')},
            'created_by': {'read_only': True}, 'source': {'read_only': True}
        }


class UserPKUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', '_public_key']

    @staticmethod
    def validate__public_key(value):
        if not validate_ssh_public_key(value):
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        return value


class UserUpdateGroupSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())

    class Meta:
        model = User
        fields = ['id', 'groups']


class UserGroupSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(
        required=False, many=True, queryset=User.objects.all(), label=_('User')
    )

    class Meta:
        model = UserGroup
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'org_id', 'name',  'users', 'comment', 'date_created',
            'created_by',
        ]
        extra_kwargs = {
            'created_by': {'label': _('Created by'), 'read_only': True}
        }


class UserGroupUpdateMemberSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all())

    class Meta:
        model = UserGroup
        fields = ['id', 'users']


class ChangeUserPasswordSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['password']
