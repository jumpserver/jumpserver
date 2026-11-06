from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from authentication.const import MFAType
from common.serializers.fields import EncryptedField, LabeledChoiceField, ListMultipleChoiceField
from common.utils import validate_ssh_public_key
from .user import UserSerializer
from ..models import User, MFAMixin, Preference


class UserUpdatePasswordSerializer(serializers.ModelSerializer):
    old_password = EncryptedField(required=True, max_length=128)
    new_password = EncryptedField(required=True, max_length=128)
    new_password_again = EncryptedField(required=True, max_length=128)

    class Meta:
        model = User
        fields = ['old_password', 'new_password', 'new_password_again']

    def validate_old_password(self, value):
        if not self.instance.check_password(value):
            msg = _('The old password is incorrect')
            raise serializers.ValidationError(msg)
        return value

    def validate_new_password(self, value):
        from ..utils import check_password_rules
        if not check_password_rules(value, is_org_admin=self.instance.is_org_admin):
            msg = _('Password does not match security rules')
            raise serializers.ValidationError(msg)
        if self.instance.is_history_password(value):
            limit_count = settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT
            msg = _('The new password cannot be the last {} passwords').format(limit_count)
            raise serializers.ValidationError(msg)
        return value

    def validate(self, values):
        new_password = values.get('new_password', '')
        new_password_again = values.get('new_password_again', '')
        if new_password != new_password_again:
            msg = _('The newly set password is inconsistent')
            raise serializers.ValidationError({'new_password_again': msg})
        return values

    def update(self, instance, validated_data):
        new_password = self.validated_data.get('new_password')
        instance.reset_password(new_password)
        return instance


class UserRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=24)
    display = serializers.CharField(max_length=64)


class UserProfileSerializer(UserSerializer):
    # Declared on UserSerializer, so Meta.read_only_fields does not apply.
    allowed_mfa_types = ListMultipleChoiceField(
        choices=MFAType.choices,
        required=False,
        allow_empty=True,
        read_only=True,
        label=_("Allowed MFA types"),
        help_text=_("Leave empty to inherit the global MFA methods"),
    )
    public_key_comment = serializers.CharField(
        source='get_public_key_comment', required=False, read_only=True, max_length=128
    )
    public_key_hash_md5 = serializers.CharField(
        source='get_public_key_hash_md5', required=False, read_only=True, max_length=128
    )
    mfa_level = LabeledChoiceField(choices=MFAMixin.MFA_LEVEL_CHOICES, label=_("MFA"), required=False)
    guide_url = serializers.SerializerMethodField()
    receive_backends = serializers.ListField(child=serializers.CharField(), read_only=True)
    lang = serializers.SerializerMethodField(label=_("Language"))

    class Meta(UserSerializer.Meta):
        read_only_fields = [
            'date_joined', 'last_login', 'created_by', 'source',
            'receive_backends', 'has_jdmc', 'allowed_mfa_types',
        ]
        fields_mini = [
            'id', 'name', 'username', 'email',
        ]
        fields = UserSerializer.Meta.fields + [
            'public_key_comment', 'public_key_hash_md5', 'guide_url',
            "wecom_id", "dingtalk_id", "feishu_id", "slack_id", 'lang', 'has_jdmc'
        ] + read_only_fields

        extra_kwargs = dict(UserSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'name': {'read_only': True, 'max_length': 128},
            'username': {'read_only': True, 'max_length': 128},
            'email': {'read_only': True},
            'is_first_login': {'label': _('Is first login'), 'read_only': False},
            'source': {'read_only': True},
            'is_valid': {'read_only': True},
            'is_active': {'read_only': True},
            'groups': {'read_only': True},
            'password_strategy': {'read_only': True},
            'date_expired': {'read_only': True},
            'date_joined': {'read_only': True},
            'last_login': {'read_only': True},
        })

        if 'password' in fields:
            fields.remove('password')
            extra_kwargs.pop('password', None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        system_roles_field = self.fields.get('system_roles')
        if system_roles_field:
            system_roles_field.read_only = True
        org_roles_field = self.fields.get('org_roles')
        if org_roles_field:
            org_roles_field.read_only = True

        if settings.PRIVACY_MODE:
            for field in (
                    'phone', 'wechat',
                    'wecom_id', 'dingtalk_id',
                    'feishu_id', 'slack_id', 'lark_id'
            ):
                self.fields.pop(field, None)

    @staticmethod
    def get_guide_url(obj) -> str:
        return settings.USER_GUIDE_URL

    def validate_mfa_level(self, mfa_level):
        if self.instance and self.instance.mfa_force_enabled:
            return 2
        return mfa_level

    def validate_public_key(self, public_key):
        if self.instance and self.instance.can_update_ssh_key():
            if not validate_ssh_public_key(public_key):
                raise serializers.ValidationError(_('Not a valid ssh public key'))
            return public_key
        return None

    def validate_password(self, password):
        from rbac.models import Role
        from ..utils import check_password_rules
        if not self.instance:
            return password

        is_org_admin = self.instance.org_roles.filter(
            name=Role.BuiltinRole.org_admin.name
        ).exsits()
        if not check_password_rules(password, is_org_admin=is_org_admin):
            msg = _('Password does not match security rules')
            raise serializers.ValidationError(msg)
        return password

    def get_lang(self, obj) -> str:
        return getattr(obj, 'lang') or settings.LANGUAGE_CODE


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


class UserOrgSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    is_default = serializers.BooleanField(read_only=True)
    is_root = serializers.BooleanField(read_only=True)
    is_system = serializers.BooleanField(read_only=True)


class UserPermsSerializer(serializers.Serializer):
    id = serializers.CharField(label=_("User ID"), read_only=True)
    username = serializers.CharField(label=_("Username"), read_only=True)
    pam_orgs = UserOrgSerializer(many=True, read_only=True)
    console_orgs = UserOrgSerializer(many=True, read_only=True)
    audit_orgs = UserOrgSerializer(many=True, read_only=True)
    workbench_orgs = UserOrgSerializer(many=True, read_only=True)
    perms = serializers.ListField(label=_("Perms"), read_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class UserLockPasswordSerializer(serializers.Serializer):
    clear = serializers.BooleanField(write_only=True, required=False, default=False)
    has_password = serializers.SerializerMethodField(label=_('Configured'))
    password = EncryptedField(required=False, allow_blank=True, max_length=128,
                              trim_whitespace=False, label=_('New password'))
    password_again = EncryptedField(required=False, allow_blank=True, max_length=128,
                                    trim_whitespace=False, label=_('Confirm password'))

    def get_has_password(self, obj):
        return Preference.objects.filter(user=self.context['request'].user, category='security',
                                         name='lock_password_hash').exists()

    def validate(self, attrs):
        password = attrs.get('password', '')
        confirmation = attrs.pop('password_again', '')
        if attrs.get('clear'):
            if password or confirmation:
                raise serializers.ValidationError({'password': _('Choose either setting or clearing the lock password.')})
            return {'clear': True}
        if password != confirmation:
            raise serializers.ValidationError({'password_again': _('The newly set password is inconsistent')})
        if not password:
            return {}
        from ..utils import check_password_rules
        if not check_password_rules(password, is_org_admin=self.context['request'].user.is_org_admin):
            raise serializers.ValidationError({'password': _('Password does not match security rules')})
        return {'password': password}

    def update(self, instance, validated_data):
        user = self.context['request'].user
        if validated_data.get('clear'):
            Preference.objects.filter(user=user, category='security', name='lock_password_hash').delete()
        password = validated_data.get('password')
        if password:
            Preference.objects.update_or_create(user=user, name='lock_password_hash', defaults={
                'category': 'security', 'value': make_password(password), 'encrypted': False,
            })
        return instance


class UserFileEncryptionSerializer(serializers.Serializer):
    has_secret_key = serializers.SerializerMethodField(label=_('Configured'))
    secret_key = EncryptedField(
        required=False, max_length=1024, write_only=True, allow_blank=True,
        label=_('New password'),
    )
    secret_key_again = EncryptedField(
        required=False, max_length=1024, write_only=True, allow_blank=True,
        label=_('Confirm password'),
    )

    def get_has_secret_key(self, obj):
        return Preference.objects.filter(
            user=self.context['request'].user, category='lina', name='secret_key',
        ).exists()

    def validate(self, attrs):
        secret_key = attrs.pop('secret_key', None)
        confirmation = attrs.pop('secret_key_again', None)
        if (secret_key or confirmation) and secret_key != confirmation:
            raise serializers.ValidationError({'secret_key_again': _('The newly set password is inconsistent')})
        if secret_key and confirmation:
            attrs['secret_key'] = secret_key
        return attrs

    def update(self, instance, validated_data):
        secret_key = validated_data.get('secret_key')
        if secret_key:
            Preference.objects.update_or_create(user=self.context['request'].user, name='secret_key', defaults={
                'category': 'lina', 'value': Preference.encrypt(secret_key), 'encrypted': True,
            })
        return instance


class UserIdleLockSerializer(serializers.Serializer):
    web_idle_lock_time = serializers.IntegerField(
        min_value=0, max_value=99999, allow_null=True, required=False,
        label=_('Web idle screen lock (minute)'),
        help_text=_('Leave blank to follow the administrator. A personal value must not exceed the administrator limit.'),
    )
    client_idle_lock_time = serializers.IntegerField(
        min_value=0, max_value=99999, allow_null=True, required=False,
        label=_('Client idle screen lock (minute)'),
        help_text=_('Leave blank to follow the administrator. A personal value must not exceed the administrator limit.'),
    )
    client_max_session_time = serializers.IntegerField(
        min_value=0, max_value=99999, allow_null=True, required=False,
        label=_('Maximum client login lifetime (minute)'),
    )
    client_reauth_on_exit = serializers.BooleanField(
        allow_null=True, required=False, label=_('Log in again after exiting the client'),
    )
    client_max_session_limit = serializers.IntegerField(read_only=True)
    effective_client_max_session_time = serializers.IntegerField(read_only=True)
    client_reauth_on_exit_required = serializers.BooleanField(read_only=True)
    effective_client_reauth_on_exit = serializers.BooleanField(read_only=True)
    web_idle_lock_limit = serializers.IntegerField(read_only=True)
    client_idle_lock_limit = serializers.IntegerField(read_only=True)
    effective_web_idle_lock_time = serializers.IntegerField(read_only=True)
    effective_client_idle_lock_time = serializers.IntegerField(read_only=True)
    client_login_policy = serializers.JSONField(read_only=True)

    def validate(self, attrs):
        from authentication.services.idle_lock import idle_lock_limits
        from authentication.services.client_login_session import client_login_policy

        if attrs.get('client_reauth_on_exit') is False and client_login_policy(use_cache=False)['reauth_on_exit']:
            raise serializers.ValidationError({
                'client_reauth_on_exit': _('The administrator requires reauthentication after client exit.'),
            })
        for name, maximum in idle_lock_limits().items():
            value = attrs.get(name)
            if value is not None and maximum > 0 and (value == 0 or value > maximum):
                raise serializers.ValidationError({
                    name: _('The administrator limit is %(minutes)s minutes. Leave blank to follow it.') % {'minutes': maximum},
                })
        return attrs

    def update(self, instance, validated_data):
        from authentication.services.idle_lock import IDLE_LOCK_CATEGORY, idle_lock_preferences

        user = self.context['request'].user
        for name, value in validated_data.items():
            if value is None:
                Preference.objects.filter(user=user, name=name, category=IDLE_LOCK_CATEGORY).delete()
            else:
                Preference.objects.update_or_create(user=user, name=name, defaults={
                    'category': IDLE_LOCK_CATEGORY, 'value': str(int(value)), 'encrypted': False,
                })
        if 'client_max_session_time' in validated_data:
            from authentication.services.client_login_session import client_login_policy, update_client_session_lifetimes
            update_client_session_lifetimes(client_login_policy(use_cache=False), user_id=user.pk)
        return idle_lock_preferences(user.pk)
