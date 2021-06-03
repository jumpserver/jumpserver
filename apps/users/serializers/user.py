# -*- coding: utf-8 -*-
#
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from django.db.models import TextChoices
from rest_framework import serializers

from common.mixins import CommonBulkSerializerMixin
from common.permissions import CanUpdateDeleteUser
from orgs.models import ROLE as ORG_ROLE
from ..models import User


__all__ = [
    'UserSerializer', 'UserRetrieveSerializer', 'MiniUserSerializer',
    'InviteSerializer', 'ServiceAccountSerializer',
]


class UserSerializer(CommonBulkSerializerMixin, serializers.ModelSerializer):
    class PasswordStrategy(TextChoices):
        email = 'email', _('Reset link will be generated and sent to the user')
        custom = 'custom', _('Set password')

    password_strategy = serializers.ChoiceField(
        choices=PasswordStrategy.choices, default=PasswordStrategy.email, required=False,
        write_only=True, label=_('Password strategy')
    )
    mfa_enabled = serializers.BooleanField(read_only=True, label=_('MFA enabled'))
    mfa_force_enabled = serializers.BooleanField(read_only=True, label=_('MFA force enabled'))
    mfa_level_display = serializers.ReadOnlyField(source='get_mfa_level_display', label=_('MFA level for display'))
    login_blocked = serializers.BooleanField(read_only=True, label=_('Login blocked'))
    is_expired = serializers.BooleanField(read_only=True, label=_('Is expired'))
    can_update = serializers.SerializerMethodField(label=_('Can update'))
    can_delete = serializers.SerializerMethodField(label=_('Can delete'))
    can_public_key_auth = serializers.ReadOnlyField(source='can_use_ssh_key_login')
    org_roles = serializers.ListField(
        label=_('Organization role name'), allow_null=True, required=False,
        child=serializers.ChoiceField(choices=ORG_ROLE.choices), default=["User"]
    )

    class Meta:
        model = User
        # mini 是指能识别对象的最小单元
        fields_mini = ['id', 'name', 'username']
        # 只能写的字段, 这个虽然无法在框架上生效，但是更多对我们是提醒
        fields_write_only = [
            'password', 'public_key',
        ]
        # small 指的是 不需要计算的直接能从一张表中获取到的数据
        fields_small = fields_mini + fields_write_only + [
            'email', 'wechat', 'phone', 'mfa_level',
            'source', 'source_display', 'can_public_key_auth', 'need_update_password',
            'mfa_enabled', 'is_valid', 'is_expired', 'is_active',  # 布尔字段
            'date_expired', 'date_joined', 'last_login',  # 日期字段
            'created_by', 'comment',  # 通用字段
            'is_wecom_bound', 'is_dingtalk_bound',
        ]
        # 包含不太常用的字段，可以没有
        fields_verbose = fields_small + [
            'total_role_display', 'org_role_display',
            'mfa_level_display', 'mfa_force_enabled', 'is_first_login',
            'date_password_last_updated', 'avatar_url',
        ]
        # 外键的字段
        fields_fk = ['role', 'role_display']
        # 多对多字段
        fields_m2m = ['groups', 'groups_display', 'org_roles']
        # 在serializer 上定义的字段
        fields_custom = ['can_update', 'can_delete', 'login_blocked', 'password_strategy']
        fields = fields_verbose + fields_fk + fields_m2m + fields_custom

        read_only_fields = [
            'date_joined', 'last_login', 'created_by', 'is_first_login',
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False, 'allow_null': True, 'allow_blank': True},
            'public_key': {'write_only': True},
            'is_first_login': {'label': _('Is first login'), 'read_only': True},
            'is_valid': {'label': _('Is valid')},
            'is_expired': {'label': _('Is expired')},
            'avatar_url': {'label': _('Avatar url')},
            'created_by': {'read_only': True, 'allow_blank': True},
            'groups_display': {'label': _('Groups name')},
            'source_display': {'label': _('Source name')},
            'org_role_display': {'label': _('Organization role name')},
            'role_display': {'label': _('Super role name')},
            'total_role_display': {'label': _('Total role name')},
            'role': {'default': "User"},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_role_choices()

    def set_role_choices(self):
        role = self.fields.get('role')
        if not role:
            return
        choices = role._choices
        choices.pop(User.ROLE.APP, None)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not request.user.is_superuser:
            choices.pop(User.ROLE.ADMIN, None)
            choices.pop(User.ROLE.AUDITOR, None)
        role._choices = choices

    def validate_role(self, value):
        request = self.context.get('request')
        if not request.user.is_superuser and value != User.ROLE.USER:
            role_display = User.ROLE.USER.label
            msg = _("Role limit to {}".format(role_display))
            raise serializers.ValidationError(msg)
        return value

    def validate_password(self, password):
        from ..utils import check_password_rules
        password_strategy = self.initial_data.get('password_strategy')
        if self.instance is None and password_strategy != self.PasswordStrategy.custom:
            # 创建用户，使用邮件设置密码
            return
        if self.instance and not password:
            # 更新用户, 未设置密码
            return
        if not check_password_rules(password):
            msg = _('Password does not match security rules')
            raise serializers.ValidationError(msg)
        return password

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


class UserRetrieveSerializer(UserSerializer):
    login_confirm_settings = serializers.PrimaryKeyRelatedField(read_only=True,
                                                                source='login_confirm_setting.reviewers', many=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['login_confirm_settings']


class MiniUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username']


class InviteSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.exclude(role=User.ROLE.APP)
    )
    role = serializers.ChoiceField(choices=ORG_ROLE.choices)


class ServiceAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'name', 'access_key']
        read_only_fields = ['access_key']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from authentication.serializers import AccessKeySerializer
        self.fields['access_key'] = AccessKeySerializer(read_only=True)

    def get_username(self):
        return self.initial_data.get('name')

    def get_email(self):
        name = self.initial_data.get('name')
        return '{}@serviceaccount.local'.format(name)

    def validate_name(self, name):
        email = self.get_email()
        username = self.get_username()
        if self.instance:
            users = User.objects.exclude(id=self.instance.id)
        else:
            users = User.objects.all()
        if users.filter(email=email) or \
                users.filter(username=username):
            raise serializers.ValidationError(_('name not unique'), code='unique')
        return name

    def save(self, **kwargs):
        self.validated_data['email'] = self.get_email()
        self.validated_data['username'] = self.get_username()
        self.validated_data['role'] = User.ROLE.APP
        return super().save(**kwargs)

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.create_access_key()
        return instance
