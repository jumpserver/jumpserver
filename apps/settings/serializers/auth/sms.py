from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.sdk.sms import BACKENDS
from common.serializers.fields import EncryptedField, PhoneField
from common.validators import PhoneValidator

__all__ = [
    'BaseSMSSettingSerializer',
    'SMSSettingSerializer', 'AlibabaSMSSettingSerializer', 'TencentSMSSettingSerializer',
    'HuaweiSMSSettingSerializer', 'CMPP2SMSSettingSerializer', 'CustomSMSSettingSerializer',
]


class SMSSettingSerializer(serializers.Serializer):
    SMS_ENABLED = serializers.BooleanField(default=False, label=_('Enable SMS'))
    SMS_BACKEND = serializers.ChoiceField(
        choices=BACKENDS.choices, default=BACKENDS.ALIBABA, label=_('SMS provider / Protocol')
    )
    SMS_CODE_LENGTH = serializers.IntegerField(
        default=4, min_value=4, max_value=16, label=_('SMS code length')
    )


class SignTmplPairSerializer(serializers.Serializer):
    SIGN_NAME = serializers.CharField(max_length=256, required=True, label=_('Signature'))
    TEMPLATE_CODE = serializers.CharField(max_length=256, required=True, label=_('Template code'))


class BaseSMSSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('SMS')

    SMS_TEST_PHONE = PhoneField(
        validators=[PhoneValidator()], required=False, allow_blank=True, allow_null=True, label=_('Test phone')
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # data['SMS_BACKEND'] = self.fields['SMS_BACKEND'].default
        return data


class AlibabaSMSSettingSerializer(BaseSMSSettingSerializer):
    ALIBABA_ACCESS_KEY_ID = serializers.CharField(max_length=256, required=True, label='Access Key ID')
    ALIBABA_ACCESS_KEY_SECRET = EncryptedField(
        max_length=256, required=False, label='Access Key Secret',
    )
    ALIBABA_VERIFY_SIGN_NAME = serializers.CharField(max_length=256, required=True, label=_('Signature'))
    ALIBABA_VERIFY_TEMPLATE_CODE = serializers.CharField(max_length=256, required=True, label=_('Template code'))


class TencentSMSSettingSerializer(BaseSMSSettingSerializer):
    TENCENT_SECRET_ID = serializers.CharField(max_length=256, required=True, label='Secret ID')
    TENCENT_SECRET_KEY = EncryptedField(max_length=256, required=False, label='Secret Key')
    TENCENT_SDKAPPID = serializers.CharField(max_length=256, required=True, label='SDK APP ID')
    TENCENT_VERIFY_SIGN_NAME = serializers.CharField(max_length=256, required=True, label=_('Signature'))
    TENCENT_VERIFY_TEMPLATE_CODE = serializers.CharField(max_length=256, required=True, label=_('Template code'))


class HuaweiSMSSettingSerializer(BaseSMSSettingSerializer):
    HUAWEI_APP_KEY = serializers.CharField(max_length=256, required=True, label='App Key')
    HUAWEI_APP_SECRET = EncryptedField(max_length=256, required=False, label='App Secret')
    HUAWEI_SMS_ENDPOINT = serializers.CharField(max_length=1024, required=True, label=_('App Access Address'))
    HUAWEI_SIGN_CHANNEL_NUM = serializers.CharField(max_length=1024, required=True, label=_('Signature channel number'))
    HUAWEI_VERIFY_SIGN_NAME = serializers.CharField(max_length=256, required=True, label=_('Signature'))
    HUAWEI_VERIFY_TEMPLATE_CODE = serializers.CharField(max_length=256, required=True, label=_('Template code'))


class CMPP2SMSSettingSerializer(BaseSMSSettingSerializer):
    CMPP2_HOST = serializers.CharField(max_length=256, required=True, label=_('Host'))
    CMPP2_PORT = serializers.IntegerField(default=7890, label=_('Port'))
    CMPP2_SP_ID = serializers.CharField(max_length=128, required=True, label=_('Enterprise code(SP id)'))
    CMPP2_SP_SECRET = EncryptedField(max_length=256, required=False, label=_('Shared secret(Shared secret)'))
    CMPP2_SRC_ID = serializers.CharField(max_length=256, required=False, label=_('Original number(Src id)'))
    CMPP2_SERVICE_ID = serializers.CharField(max_length=256, required=True, label=_('Business type(Service id)'))
    CMPP2_VERIFY_SIGN_NAME = serializers.CharField(max_length=256, required=True, label=_('Signature'))
    CMPP2_VERIFY_TEMPLATE_CODE = serializers.CharField(
        max_length=69, required=True, label=_('Template'),
        help_text=_('Template need contain {code} and Signature + template length does not exceed 67 words. '
                    'For example, your verification code is {code}, which is valid for 5 minutes. '
                    'Please do not disclose it to others.')
    )

    def validate(self, attrs):
        sign_name = attrs.get('CMPP2_VERIFY_SIGN_NAME', '')
        template_code = attrs.get('CMPP2_VERIFY_TEMPLATE_CODE', '')
        if template_code.find('{code}') == -1:
            raise serializers.ValidationError(_('The template needs to contain {code}'))
        if len(sign_name + template_code) > 65:
            # 保证验证码内容在一条短信中(长度小于70字), 签名两边的括号和空格占3个字，再减去2个即可(验证码占用4个但占位符6个
            raise serializers.ValidationError(_('Signature + Template must not exceed 65 words'))
        return attrs


class CustomSMSSettingSerializer(BaseSMSSettingSerializer):
    class RequestType(models.TextChoices):
        get = 'get', 'Get'
        post = 'post', 'Post'

    CUSTOM_SMS_URL = serializers.URLField(required=True, label=_("URL"))
    CUSTOM_SMS_API_PARAMS = serializers.JSONField(
        label=_('Parameters'), default={'phone_number': '{phone_number}', 'code': '{code}'}
    )
    CUSTOM_SMS_REQUEST_METHOD = serializers.ChoiceField(
        default=RequestType.get, choices=RequestType.choices, label=_("Request method")
    )

    def validate(self, attrs):
        need_params = {'{phone_numbers}', '{code}'}
        params = attrs.get('CUSTOM_SMS_API_PARAMS', {})
        # 这里用逗号分隔是保证需要的参数必须是完整的，不能分开在不同的参数中首位相连
        params_string = ','.join(params.values())
        for param in need_params:
            if param not in params_string:
                raise serializers.ValidationError(
                _('The value in the parameter must contain %s') % ','.join(need_params)
            )
        return attrs
