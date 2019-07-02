# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from common.utils import get_signer, validate_ssh_public_key
from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from orgs.mixins import BulkOrgResourceModelSerializer
from ..models import User, UserGroup

signer = get_signer()


class UserSerializer(BulkSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = User
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'username', 'password', 'email', 'public_key',
            'groups',  'groups_display',
            'role', 'role_display',  'wechat', 'phone', 'otp_level',
            'comment', 'source', 'source_display', 'is_valid', 'is_expired',
            'is_active', 'created_by', 'is_first_login',
            'date_password_last_updated', 'date_expired', 'avatar_url',
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'public_key': {'write_only': True},
            'groups_display': {'label': _('Groups name')},
            'source_display': {'label': _('Source name')},
            'is_first_login': {'label': _('Is first login'), 'read_only': True},
            'role_display': {'label': _('Role name')},
            'is_valid': {'label': _('Is valid')},
            'is_expired': {'label': _('Is expired')},
            'avatar_url': {'label': _('Avatar url')},
            'created_by': {'read_only': True}, 'source': {'read_only': True}
        }

    @staticmethod
    def validate_password(value):
        from ..utils import check_password_rules
        if not check_password_rules(value):
            msg = _('Password does not match security rules')
            raise serializers.ValidationError(msg)
        return value

    @staticmethod
    def change_password_to_raw(validated_data):
        password = validated_data.pop('password', None)
        if password:
            validated_data['password_raw'] = password
        return validated_data

    def create(self, validated_data):
        validated_data = self.change_password_to_raw(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self.change_password_to_raw(validated_data)
        return super().update(instance, validated_data)


class UserPKUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'public_key']

    @staticmethod
    def validate_public_key(value):
        if not validate_ssh_public_key(value):
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        return value


class UserUpdateGroupSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())

    class Meta:
        model = User
        fields = ['id', 'groups']


class UserGroupSerializer(BulkOrgResourceModelSerializer):
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
