from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField, LabeledChoiceField
from common.utils import validate_ssh_public_key
from .user import UserSerializer
from ..models import User


class UserOrgSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    is_default = serializers.BooleanField(read_only=True)
    is_root = serializers.BooleanField(read_only=True)


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


class UserUpdatePublicKeySerializer(serializers.ModelSerializer):
    public_key_comment = serializers.CharField(
        source='get_public_key_comment', required=False, read_only=True, max_length=128
    )
    public_key_hash_md5 = serializers.CharField(
        source='get_public_key_hash_md5', required=False, read_only=True, max_length=128
    )

    class Meta:
        model = User
        fields = ['public_key_comment', 'public_key_hash_md5', 'public_key']
        extra_kwargs = {
            'public_key': {'required': True, 'write_only': True, 'max_length': 2048}
        }

    @staticmethod
    def validate_public_key(value):
        if not validate_ssh_public_key(value):
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        return value

    def update(self, instance, validated_data):
        new_public_key = self.validated_data.get('public_key')
        instance.set_public_key(new_public_key)
        return instance


class UserRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=24)
    display = serializers.CharField(max_length=64)


class UserProfileSerializer(UserSerializer):
    MFA_LEVEL_CHOICES = (
        (0, _('Disable')),
        (1, _('Enable')),
        (2, _("Force enable")),
    )
    public_key_comment = serializers.CharField(
        source='get_public_key_comment', required=False, read_only=True, max_length=128
    )
    public_key_hash_md5 = serializers.CharField(
        source='get_public_key_hash_md5', required=False, read_only=True, max_length=128
    )
    mfa_level = LabeledChoiceField(choices=MFA_LEVEL_CHOICES, label=_("MFA"), required=False)
    guide_url = serializers.SerializerMethodField()
    receive_backends = serializers.ListField(child=serializers.CharField(), read_only=True)
    console_orgs = UserOrgSerializer(many=True, read_only=True)
    audit_orgs = UserOrgSerializer(many=True, read_only=True)
    workbench_orgs = UserOrgSerializer(many=True, read_only=True)
    perms = serializers.ListField(label=_("Perms"), read_only=True)

    class Meta(UserSerializer.Meta):
        read_only_fields = [
            'date_joined', 'last_login', 'created_by', 'source',
            'console_orgs', 'audit_orgs', 'workbench_orgs',
            'receive_backends', 'perms',
        ]
        fields_mini = [
            'id', 'name', 'username', 'email',
        ]
        fields = UserSerializer.Meta.fields + [
            'public_key_comment', 'public_key_hash_md5', 'guide_url',
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

    @staticmethod
    def get_guide_url(obj):
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
