# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from common.utils import get_signer, validate_ssh_public_key
from common.mixins import BulkSerializerMixin
from common.fields import StringManyToManyField
from common.serializers import AdaptedBulkListSerializer
from orgs.mixins import BulkOrgResourceModelSerializer
from ..models import User, UserGroup


__all__ = [
    'UserSerializer', 'UserPKUpdateSerializer', 'UserUpdateGroupSerializer',
    'UserGroupSerializer', 'UserGroupListSerializer',
    'UserGroupUpdateMemberSerializer', 'ChangeUserPasswordSerializer'
]


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
            'password': {'write_only': True, 'required': False, 'allow_null': True, 'allow_blank': True},
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

    def validate_role(self, value):
        request = self.context.get('request')
        if not request.user.is_superuser and value != User.ROLE_USER:
            role_display = dict(User.ROLE_CHOICES)[User.ROLE_USER]
            msg = _("Role limit to {}".format(role_display))
            raise serializers.ValidationError(msg)
        return value

    def validate_password(self, password):
        from ..utils import check_password_rules
        password_strategy = self.initial_data.get('password_strategy')
        if password_strategy == '0':
            return
        if password_strategy is None and not password:
            return
        if not check_password_rules(password):
            msg = _('Password does not match security rules')
            raise serializers.ValidationError(msg)
        return password

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
            'id', 'name',  'users', 'comment', 'date_created',
            'created_by',
        ]
        extra_kwargs = {
            'created_by': {'label': _('Created by'), 'read_only': True}
        }


class UserGroupListSerializer(UserGroupSerializer):
    users = StringManyToManyField(many=True, read_only=True)


class UserGroupUpdateMemberSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all())

    class Meta:
        model = UserGroup
        fields = ['id', 'users']


class ChangeUserPasswordSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['password']
