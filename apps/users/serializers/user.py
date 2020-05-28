# -*- coding: utf-8 -*-
#
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.utils import validate_ssh_public_key
from common.mixins import CommonBulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from common.permissions import CanUpdateDeleteUser
from ..models import User


__all__ = [
    'UserSerializer', 'UserPKUpdateSerializer',
    'ChangeUserPasswordSerializer', 'ResetOTPSerializer',
    'UserProfileSerializer', 'UserOrgSerializer'
]


class UserOrgSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class UserSerializer(CommonBulkSerializerMixin, serializers.ModelSerializer):
    EMAIL_SET_PASSWORD = _('Reset link will be generated and sent to the user')
    CUSTOM_PASSWORD = _('Set password')
    PASSWORD_STRATEGY_CHOICES = (
        (0, EMAIL_SET_PASSWORD),
        (1, CUSTOM_PASSWORD)
    )
    password_strategy = serializers.ChoiceField(
        choices=PASSWORD_STRATEGY_CHOICES, required=False, initial=0,
        label=_('Password strategy'), write_only=True
    )
    mfa_level_display = serializers.ReadOnlyField(source='get_mfa_level_display')
    login_blocked = serializers.SerializerMethodField()
    can_update = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    key_prefix_block = "_LOGIN_BLOCK_{}"

    class Meta:
        model = User
        list_serializer_class = AdaptedBulkListSerializer
        # mini 是指能识别对象的最小单元
        fields_mini = ['id', 'name', 'username']
        # small 指的是 不需要计算的直接能从一张表中获取到的数据
        fields_small = fields_mini + [
            'password', 'email', 'public_key', 'wechat', 'phone', 'mfa_level', 'mfa_enabled',
            'mfa_level_display', 'mfa_force_enabled',
            'comment', 'source', 'is_valid', 'is_expired',
            'is_active', 'created_by', 'is_first_login',
            'password_strategy', 'date_password_last_updated', 'date_expired',
            'avatar_url', 'source_display', 'date_joined', 'last_login'
        ]
        fields = fields_small + [
            'groups', 'role', 'groups_display', 'role_display',
            'can_update', 'can_delete', 'login_blocked',
        ]

        extra_kwargs = {
            'password': {'write_only': True, 'required': False, 'allow_null': True, 'allow_blank': True},
            'public_key': {'write_only': True},
            'is_first_login': {'label': _('Is first login'), 'read_only': True},
            'is_valid': {'label': _('Is valid')},
            'is_expired': {'label': _('Is expired')},
            'avatar_url': {'label': _('Avatar url')},
            'created_by': {'read_only': True, 'allow_blank': True},
            'can_update': {'read_only': True},
            'can_delete': {'read_only': True},
            'groups_display': {'label': _('Groups name')},
            'source_display': {'label': _('Source name')},
            'role_display': {'label': _('Role name')},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_role_choices()

    def set_role_choices(self):
        role = self.fields.get('role')
        if not role:
            return
        choices = role._choices
        choices.pop('App', None)
        role._choices = choices

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

    def validate_groups(self, groups):
        """
        审计员不能加入到组中
        """
        role = self.initial_data.get('role')
        if self.instance:
            role = role or self.instance.role
        if role == User.ROLE_AUDITOR:
            return []
        return groups

    @staticmethod
    def change_password_to_raw(attrs):
        password = attrs.pop('password', None)
        if password:
            attrs['password_raw'] = password
        return attrs

    @staticmethod
    def clean_auth_fields(attrs):
        for field in ('password', 'public_key'):
            value = attrs.get(field)
            if not value:
                attrs.pop(field, None)
        return attrs

    def validate(self, attrs):
        attrs = self.change_password_to_raw(attrs)
        attrs = self.clean_auth_fields(attrs)
        attrs.pop('password_strategy', None)
        return attrs

    def get_can_update(self, obj):
        return CanUpdateDeleteUser.has_update_object_permission(
            self.context['request'], self.context['view'], obj
        )

    def get_can_delete(self, obj):
        return CanUpdateDeleteUser.has_delete_object_permission(
            self.context['request'], self.context['view'], obj
        )

    def get_login_blocked(self, obj):
        key_block = self.key_prefix_block.format(obj.username)
        blocked = bool(cache.get(key_block))
        return blocked


class UserPKUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'public_key']

    @staticmethod
    def validate_public_key(value):
        if not validate_ssh_public_key(value):
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        return value


class ChangeUserPasswordSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['password']


class ResetOTPSerializer(serializers.Serializer):
    msg = serializers.CharField(read_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class UserRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=24)
    display = serializers.CharField(max_length=64)


class UserProfileSerializer(UserSerializer):
    admin_or_audit_orgs = UserOrgSerializer(many=True, read_only=True)
    current_org_roles = serializers.ListField(read_only=True)
    public_key_comment = serializers.SerializerMethodField()
    public_key_hash_md5 = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'public_key_comment', 'public_key_hash_md5', 'admin_or_audit_orgs', 'current_org_roles'
        ]
        extra_kwargs = dict(UserSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'name': {'read_only': True, 'max_length': 128},
            'username': {'read_only': True, 'max_length': 128},
            'email': {'read_only': True},
            'mfa_level': {'read_only': True},
            'source': {'read_only': True},
            'is_valid': {'read_only': True},
            'is_active': {'read_only': True},
            'groups': {'read_only': True},
            'roles': {'read_only': True},
            'password_strategy': {'read_only': True},
            'date_expired': {'read_only': True},
            'date_joined': {'read_only': True},
            'last_login': {'read_only': True},
            'role': {'read_only': True},
        })

        if 'password' in fields:
            fields.remove('password')
            extra_kwargs.pop('password', None)

        if 'public_key' in fields:
            fields.remove('public_key')
            extra_kwargs.pop('public_key', None)

    @staticmethod
    def get_public_key_comment(obj):
        return obj.public_key_obj.comment

    @staticmethod
    def get_public_key_hash_md5(obj):
        if callable(obj.public_key_obj.hash_md5):
            return obj.public_key_obj.hash_md5()
        return ''
