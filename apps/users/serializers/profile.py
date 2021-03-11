from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.utils import validate_ssh_public_key
from ..models import User

from .user import UserSerializer


class UserOrgSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class UserOrgLabelSerializer(serializers.Serializer):
    value = serializers.CharField(source='id')
    label = serializers.CharField(source='name')


class UserUpdatePasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(required=True, max_length=128, write_only=True)
    new_password = serializers.CharField(required=True, max_length=128, write_only=True)
    new_password_again = serializers.CharField(required=True, max_length=128, write_only=True)

    class Meta:
        model = User
        fields = ['old_password', 'new_password', 'new_password_again']

    def validate_old_password(self, value):
        if not self.instance.check_password(value):
            msg = _('The old password is incorrect')
            raise serializers.ValidationError(msg)
        return value

    @staticmethod
    def validate_new_password(value):
        from ..utils import check_password_rules
        if not check_password_rules(value):
            msg = _('Password does not match security rules')
            raise serializers.ValidationError(msg)
        return value

    def validate_new_password_again(self, value):
        if value != self.initial_data.get('new_password', ''):
            msg = _('The newly set password is inconsistent')
            raise serializers.ValidationError(msg)
        return value

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
    admin_or_audit_orgs = UserOrgSerializer(many=True, read_only=True)
    user_all_orgs = UserOrgLabelSerializer(many=True, read_only=True)
    current_org_roles = serializers.ListField(read_only=True)
    public_key_comment = serializers.CharField(
        source='get_public_key_comment', required=False, read_only=True, max_length=128
    )
    public_key_hash_md5 = serializers.CharField(
        source='get_public_key_hash_md5', required=False, read_only=True, max_length=128
    )
    MFA_LEVEL_CHOICES = (
        (0, _('Disable')),
        (1, _('Enable')),
    )
    mfa_level = serializers.ChoiceField(choices=MFA_LEVEL_CHOICES, label=_('MFA'), required=False)
    guide_url = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'public_key_comment', 'public_key_hash_md5', 'admin_or_audit_orgs', 'current_org_roles',
            'guide_url', 'user_all_orgs'
        ]
        read_only_fields = [
            'date_joined', 'last_login', 'created_by', 'source'
        ]
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
