# -*- coding: utf-8 -*-
#
from functools import partial

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers import ResourceLabelsMixin, CommonBulkModelSerializer
from common.serializers.fields import (
    EncryptedField,
    ObjectRelatedField,
    LabeledChoiceField,
    PhoneField,
)
from common.utils import pretty_string, get_logger
from common.validators import PhoneValidator
from jumpserver.utils import get_current_request
from orgs.utils import current_org
from rbac.builtin import BuiltinRole
from rbac.models import OrgRoleBinding, SystemRoleBinding, Role
from rbac.permissions import RBACPermission
from users.signals import post_user_change_password
from ..const import PasswordStrategy
from ..models import User

__all__ = [
    "UserSerializer",
    "SmsUserSerializer",
    "MiniUserSerializer",
    "InviteSerializer",
    "ServiceAccountSerializer",
    "UserRetrieveSerializer",
]

logger = get_logger(__file__)


def default_system_roles():
    return [BuiltinRole.system_user.get_role()]


def default_org_roles():
    return [BuiltinRole.org_user.get_role()]


class RolesSerializerMixin(serializers.Serializer):
    system_roles = ObjectRelatedField(
        queryset=Role.system_roles,
        attrs=("id", "display_name"),
        label=_("System roles"),
        many=True,
        default=default_system_roles,
        help_text=_(
            "System roles are roles at the system level, and they will take effect across all organizations"
        ),
    )
    org_roles = ObjectRelatedField(
        queryset=Role.org_roles,
        attrs=("id", "display_name", "name"),
        label=_("Org roles"),
        many=True,
        required=False,
        default=default_org_roles,
        help_text=_(
            "Org roles are roles at the organization level, and they will only take effect within current organization"
        ),
    )
    orgs_roles = serializers.JSONField(
        read_only=True, label=_("Organizations and roles")
    )

    def pop_roles_if_need(self, fields):
        request = self.context.get("request")
        view = self.context.get("view")

        if not all([request, view, hasattr(view, "action")]):
            return fields
        if request.user.is_anonymous:
            return fields

        model_cls_field_mapper = {
            SystemRoleBinding: ["system_roles"],
            OrgRoleBinding: ["org_roles", "orgs_roles"],
        }

        update_actions = (
            "partial_bulk_update",
            "bulk_update",
            "partial_update",
            "update",
        )
        action = view.action or "list"
        if action in update_actions:
            action = "create"

        for model_cls, fields_names in model_cls_field_mapper.items():
            perms = RBACPermission.parse_action_model_perms(action, model_cls)
            if request.user.has_perms(perms):
                continue
            # 没有权限就去掉
            for field_name in fields_names:
                fields.pop(field_name, None)
        return fields

    def get_fields(self):
        fields = super().get_fields()
        self.pop_roles_if_need(fields)
        return fields


class UserSerializer(
    RolesSerializerMixin, ResourceLabelsMixin, CommonBulkModelSerializer
):
    password_strategy = LabeledChoiceField(
        choices=PasswordStrategy.choices,
        default=PasswordStrategy.email,
        allow_null=True,
        required=False,
        label=_("Password setting"),
    )
    mfa_enabled = serializers.BooleanField(read_only=True, label=_("MFA enabled"))
    mfa_force_enabled = serializers.BooleanField(
        read_only=True, label=_("MFA force enabled")
    )
    login_blocked = serializers.BooleanField(read_only=True, label=_("Login blocked"))
    is_expired = serializers.BooleanField(read_only=True, label=_("Is expired"))
    is_valid = serializers.BooleanField(read_only=True, label=_("Is valid"))
    is_otp_secret_key_bound = serializers.BooleanField(
        read_only=True, label=_("Is OTP bound")
    )
    is_superuser = serializers.BooleanField(
        read_only=True, label=_("Super Administrator")
    )
    is_org_admin = serializers.BooleanField(
        read_only=True, label=_("Organization Administrator")
    )
    can_public_key_auth = serializers.BooleanField(
        source="can_use_ssh_key_login",
        label=_("Can public key authentication"),
        read_only=True,
    )
    password = EncryptedField(
        label=_("Password"),
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=1024,
    )
    phone = PhoneField(
        validators=[PhoneValidator()],
        required=False,
        allow_blank=True,
        allow_null=True,
        label=_("Phone"),
    )
    custom_m2m_fields = {
        "system_roles": [BuiltinRole.system_user],
        "org_roles": [BuiltinRole.org_user],
    }

    class Meta:
        model = User
        # mini 是指能识别对象的最小单元
        fields_mini = ["id", "name", "username"]
        # 只能写的字段, 这个虽然无法在框架上生效，但是更多对我们是提醒
        fields_write_only = [
            "password",
            "public_key",
        ]
        # xpack 包含的字段
        fields_xpack = ["wecom_id", "dingtalk_id", "feishu_id", "lark_id", "slack_id", "is_org_admin", "orgs_roles",
                        "org_roles"]
        # small 指的是 不需要计算的直接能从一张表中获取到的数据
        fields_small = (
            fields_mini
            + fields_write_only
            + [
                "email",
                "wechat",
                "phone",
                "mfa_level",
                "source",
                *fields_xpack,
                "created_by",
                "updated_by",
                "comment",  # 通用字段
            ]
        )
        fields_date = [
            "date_expired",
            "date_joined",
            "last_login",
            "date_updated",
            "date_api_key_last_used",
        ]
        fields_bool = [
            "is_superuser",
            "is_org_admin",
            "is_service_account",
            "is_valid",
            "is_expired",
            "is_active",  # 布尔字段
            "is_otp_secret_key_bound",
            "can_public_key_auth",
            "mfa_enabled",
            "need_update_password",
        ]
        # 包含不太常用的字段，可以没有
        fields_verbose = (
            fields_small
            + fields_date
            + fields_bool
            + [
                "mfa_force_enabled",
                "is_first_login",
                "date_password_last_updated",
                "avatar_url",
            ]
        )
        # 外键的字段
        fields_fk = []
        # 多对多字段
        fields_m2m = ["groups", "system_roles", "org_roles", "orgs_roles", "labels"]
        # 在serializer 上定义的字段
        fields_custom = ["login_blocked", "password_strategy"]
        fields = fields_verbose + fields_fk + fields_m2m + fields_custom
        fields_unexport = ["avatar_url", "is_service_account"]

        read_only_fields = [
            "date_joined",
            "last_login",
            "created_by",
            "is_first_login",
            *fields_xpack,
            "date_api_key_last_used",
        ]
        fields_only_root_org = ["orgs_roles"]
        disallow_self_update_fields = ["is_active", "system_roles", "org_roles"]
        extra_kwargs = {
            "name": {
                "help_text": _("Full name"),
            },
            "username": {
                "help_text": _("Login username"),
            },
            "email": {
                "help_text": _("Email address"),
            },
            "password": {
                "write_only": True,
                "required": False,
                "allow_null": True,
                "allow_blank": True,
            },
            "groups": {
                "label": _("Groups"),
                "help_text": _("User groups to join"),
            },
            "source": {
                "help_text": _(
                    "User source identifies where the user was created, which could be AD or other sources."
                    "There are security settings that can restrict users to log in to the system only from the sources."
                ),
            },
            "is_superuser": {"label": _("Superuser")},
            "public_key": {"write_only": True},
            "is_first_login": {"label": _("Is first login"), "read_only": True},
            "is_active": {"label": _("Is active"), "help_text": ""},
            "is_valid": {"label": _("Is valid")},
            "is_service_account": {"label": _("Is service account")},
            "is_org_admin": {"label": _("Is org admin")},
            "is_expired": {"label": _("Is expired")},
            "avatar_url": {"label": _("Avatar url")},
            "created_by": {"read_only": True, "allow_blank": True},
            "role": {"default": "User"},
            "is_otp_secret_key_bound": {"label": _("Is OTP bound")},
            "mfa_level": {
                "label": _("MFA level"),
                "help_text": _("Multi-Factor Authentication"),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_source_choices()

    def get_fields(self):
        fields = super().get_fields()
        self.pop_fields_if_need(fields)
        return fields

    def pop_fields_if_need(self, fields):
        # pop only root org fields
        if not current_org.is_root():
            for f in self.Meta.fields_only_root_org:
                fields.pop(f, None)

    def update_source_choices(self):
        source = self.fields.get("source")
        if not source:
            return
        open_source = ["local", "ldap", "cas"]
        choices = dict(source.choices)
        if not settings.XPACK_ENABLED:
            choices = {k: v for k, v in choices.items() if k in open_source}
        source.choices = list(choices.items())

    def validate_password(self, password):
        password_strategy = self.initial_data.get("password_strategy")
        if self.instance is None and password_strategy != PasswordStrategy.custom:
            # 创建用户，使用邮件设置密码
            return
        if self.instance and not password:
            # 更新用户, 未设置密码
            return
        return password

    @staticmethod
    def change_password_to_raw(attrs):
        password = attrs.pop("password", None)
        if password:
            attrs["password_raw"] = password
        return attrs

    @staticmethod
    def clean_auth_fields(attrs):
        for field in ("password", "public_key"):
            value = attrs.get(field)
            if not value:
                attrs.pop(field, None)
        return attrs

    def check_disallow_self_update_fields(self, attrs):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return attrs
        if not self.instance:
            return attrs
        if request.user.id != self.instance.id:
            return attrs
        disallow_fields = set(list(attrs.keys())) & set(
            self.Meta.disallow_self_update_fields
        )
        if not disallow_fields:
            return attrs
        # 用户自己不能更新自己的一些字段
        logger.debug("Disallow update self fields: %s", disallow_fields)
        for field in disallow_fields:
            attrs.pop(field, None)
        return attrs

    def validate(self, attrs):
        attrs = self.check_disallow_self_update_fields(attrs)
        attrs = self.change_password_to_raw(attrs)
        attrs = self.clean_auth_fields(attrs)
        password_strategy = attrs.pop("password_strategy", None)
        request = get_current_request()
        if request:
            request.password_strategy = password_strategy
        return attrs

    def save_and_set_custom_m2m_fields(self, validated_data, save_handler, created):
        m2m_values = {}
        for f, default_roles in self.custom_m2m_fields.items():
            roles = validated_data.pop(f, None)
            if created and not roles:
                roles = [
                    Role.objects.filter(id=role.id).first() for role in default_roles
                ]
            m2m_values[f] = roles

        instance = save_handler(validated_data)
        for field_name, value in m2m_values.items():
            if value is None:
                continue
            field = getattr(instance, field_name)
            field.set(value)
        return instance

    def update(self, instance, validated_data):
        save_handler = partial(super().update, instance)
        instance = self.save_and_set_custom_m2m_fields(
            validated_data, save_handler, created=False
        )
        if validated_data.get('public_key'):
            post_user_change_password.send(instance.__class__, user=instance)
        return instance

    def create(self, validated_data):
        save_handler = super().create
        instance = self.save_and_set_custom_m2m_fields(
            validated_data, save_handler, created=True
        )
        if validated_data.get('public_key'):
            post_user_change_password.send(instance.__class__, user=instance)
        return instance

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.prefetch_related("groups", "labels", "labels__label")
        return queryset


class UserRetrieveSerializer(UserSerializer):
    login_confirm_settings = serializers.PrimaryKeyRelatedField(
        read_only=True, source="login_confirm_setting.reviewers", many=True
    )

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["login_confirm_settings"]


class SmsUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'email', 'phone', 'source', 'is_active', 'comment'
        ]


class MiniUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = UserSerializer.Meta.fields_mini


class InviteSerializer(RolesSerializerMixin, serializers.Serializer):
    users = serializers.PrimaryKeyRelatedField(
        queryset=User.get_nature_users(),
        many=True,
        label=_("Users"),
        help_text=_(
            "* For security, only a partial of users is displayed. You can search for more"
        ),
    )
    system_roles = None


class ServiceAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "access_key", "comment"]
        read_only_fields = ["access_key"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from authentication.serializers import AccessKeyCreateSerializer

        self.fields["access_key"] = AccessKeyCreateSerializer(read_only=True)

    def get_username(self):
        return self.initial_data.get("name")

    def get_email(self):
        name = self.initial_data.get("name")
        name_max_length = 128 - len(User.service_account_email_suffix)
        name = pretty_string(name, max_length=name_max_length, ellipsis_str="-")
        return "{}{}".format(name, User.service_account_email_suffix)

    def validate_name(self, name):
        email = self.get_email()
        username = self.get_username()
        if self.instance:
            users = User.objects.exclude(id=self.instance.id)
        else:
            users = User.objects.all()
        if users.filter(email=email) or users.filter(username=username):
            raise serializers.ValidationError(_("name not unique"), code="unique")
        return name

    def create(self, validated_data):
        name = validated_data["name"]
        email = self.get_email()
        comment = validated_data.get("comment", "")
        user, ak = User.create_service_account(name, email, comment)
        return user
