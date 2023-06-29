# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.cache import cache
from rest_framework import serializers

from authentication.utils import check_captcha_is_valid
from common.serializers.fields import EncryptedField
from common.utils import get_object_or_none, random_string
from users.models import User


__all__ = [
    'MFAChallengeSerializer', 'MFASelectTypeSerializer',
    'PasswordVerifySerializer', 'ResetPasswordCodeSerializer',
    'ForgetPasswordPreviewingSerializer', 'ForgetPasswordAuthSerializer',
    'LoginSerializer', 'LoginCaptchaSerializer', 'ResetPasswordSerializer'
]


class ResetPasswordCodeSerializer(serializers.Serializer):
    form_type = serializers.ChoiceField(
        choices=[('sms', _('SMS')), ('email', _('Email'))], default='email'
    )
    email = serializers.CharField(allow_blank=True)
    sms = serializers.CharField(allow_blank=True)

    def create(self, attrs):
        error = []
        validate_backends = {
            'email': _('Email'), 'sms': _('SMS')
        }
        form_type = attrs.get('form_type', 'email')
        validate_backend_input = attrs.get(form_type)
        if not validate_backend_input:
            error.append(_('The {} cannot be empty').format(
                validate_backends.get(validate_backend_input))
            )
        if error:
            raise serializers.ValidationError(error)


class PasswordVerifySerializer(serializers.Serializer):
    password = EncryptedField()


class MFASelectTypeSerializer(serializers.Serializer):
    type = serializers.CharField()
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class MFAChallengeSerializer(serializers.Serializer):
    type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    code = serializers.CharField(write_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class CaptchaSerializer(serializers.Serializer):
    value = serializers.CharField(required=True)
    key = serializers.CharField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    new_password = EncryptedField(max_length=1024, required=True, label=_('New password'))
    confirm_password = EncryptedField(max_length=1024, required=True, label=_('Confirm password'))

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'error': _('Password does not match')})
        return attrs


class ForgetPasswordPreviewingSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True, label=_("Username"))
    code = CaptchaSerializer()
    token = serializers.CharField(max_length=36, read_only=True)

    @staticmethod
    def custom_validate_username(username):
        err = ''
        user = get_object_or_none(User, username=username)
        if not user:
            err = _('User does not exist: {}').format(username)
        if settings.ONLY_ALLOW_AUTH_FROM_SOURCE and not user.is_local:
            err = _('Non-local users can log in only from third-party platforms '
                    'and cannot change their passwords: {}').format(username)
        return user, err

    @staticmethod
    def custom_validate_code(code_dict):
        return check_captcha_is_valid(code_dict)

    def create(self, validated_data):
        user, err = self.custom_validate_username(validated_data['username'])
        if err:
            raise serializers.ValidationError({'username': err})

        err = self.custom_validate_code(validated_data.get('code', {}))
        if err:
            raise serializers.ValidationError({'code': err})

        token = random_string(36)
        user_map = {
            'username': user.username, 'phone': user.phone,
            'email': user.email, 'receive_backends': user.receive_backends
        }
        cache.set(token, user_map, 5 * 60)
        validated_data['token'] = token
        return validated_data


class ForgetPasswordAuthSerializer(serializers.Serializer):
    methods = serializers.CharField(label=_('Authentication backend'))
    account = serializers.CharField(max_length=36, required=True)
    code = serializers.CharField(max_length=36, required=True, label=_('Captcha'))


def get_auto_login_label():
    days_auto_login = int(settings.SESSION_COOKIE_AGE / 3600 / 24)
    return _("{} days auto login").format(days_auto_login or 1)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=128, required=True, label=_('Username'))
    password = EncryptedField(max_length=1024, required=True, label=_('Password'))
    auto_login = serializers.BooleanField(default=False, label=get_auto_login_label())


class LoginCaptchaSerializer(LoginSerializer):
    has_captcha = serializers.BooleanField(default=True)
    captcha = CaptchaSerializer()

    def validate(self, attrs):
        err = check_captcha_is_valid(attrs['captcha'])
        if err:
            raise serializers.ValidationError({'captcha': err})
        return attrs

