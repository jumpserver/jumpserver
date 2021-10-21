from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.sdk.sms import BACKENDS

__all__ = ['SMSSettingSerializer', 'AlibabaSMSSettingSerializer', 'TencentSMSSettingSerializer']


class SMSSettingSerializer(serializers.Serializer):
    SMS_ENABLED = serializers.BooleanField(default=False, label=_('Enable SMS'))
    SMS_BACKEND = serializers.ChoiceField(
        choices=BACKENDS.choices, default=BACKENDS.ALIBABA, label=_('SMS provider')
    )


class SignTmplPairSerializer(serializers.Serializer):
    SIGN_NAME = serializers.CharField(max_length=256, required=True, label=_('Signature'))
    TEMPLATE_CODE = serializers.CharField(max_length=256, required=True, label=_('Template code'))


class BaseSMSSettingSerializer(serializers.Serializer):
    SMS_TEST_PHONE = serializers.CharField(max_length=256, required=False, allow_blank=True, label=_('Test phone'))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # data['SMS_BACKEND'] = self.fields['SMS_BACKEND'].default
        return data


class AlibabaSMSSettingSerializer(BaseSMSSettingSerializer):
    ALIBABA_ACCESS_KEY_ID = serializers.CharField(max_length=256, required=True, label='AccessKeyId')
    ALIBABA_ACCESS_KEY_SECRET = serializers.CharField(
        max_length=256, required=False, label='AccessKeySecret', write_only=True
    )
    ALIBABA_VERIFY_SIGN_NAME = serializers.CharField(max_length=256, required=True, label=_('Signature'))
    ALIBABA_VERIFY_TEMPLATE_CODE = serializers.CharField(max_length=256, required=True, label=_('Template code'))


class TencentSMSSettingSerializer(BaseSMSSettingSerializer):
    TENCENT_SECRET_ID = serializers.CharField(max_length=256, required=True, label='Secret id')
    TENCENT_SECRET_KEY = serializers.CharField(max_length=256, required=False, label='Secret key', write_only=True)
    TENCENT_SDKAPPID = serializers.CharField(max_length=256, required=True, label='SDK app id')
    TENCENT_VERIFY_SIGN_NAME = serializers.CharField(max_length=256, required=True, label=_('Signature'))
    TENCENT_VERIFY_TEMPLATE_CODE = serializers.CharField(max_length=256, required=True, label=_('Template code'))
