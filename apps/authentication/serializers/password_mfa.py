# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import serializers
from captcha.models import CaptchaStore

from common.serializers.fields import EncryptedField
from common.utils import get_object_or_none, random_string
from users.models import User


__all__ = [
    'MFAChallengeSerializer', 'MFASelectTypeSerializer',
    'PasswordVerifySerializer', 'ResetPasswordCodeSerializer',
    'ForgetPasswordPreviewingSerializer', 'ForgetPasswordAuthSerializer',
    'LoginSerializer',
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
        err = ''
        key, value = code_dict.get('key'), code_dict.get('value')
        if not getattr(settings, 'CAPTCHA_GET_FROM_POOL', None):
            CaptchaStore.remove_expired()

        try:
            captcha = CaptchaStore.objects.get(
                hashkey=key, expiration__gt=timezone.now()
            )
        except CaptchaStore.DoesNotExist:
            err = _('Invalid CAPTCHA')
        else:
            if captcha.response != value:
                err = _('Invalid CAPTCHA')
            captcha.delete()
        return err

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
    password = serializers.CharField(max_length=128, required=True, label=_('Password'))
    auto_login = serializers.BooleanField(default=False, label=get_auto_login_label())

