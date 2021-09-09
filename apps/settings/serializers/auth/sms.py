from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.message.backends.sms import BACKENDS

__all__ = ['AlibabaSMSSettingSerializer', 'TencentSMSSettingSerializer']


class BaseSMSSettingSerializer(serializers.Serializer):
    SMS_ENABLED = serializers.BooleanField(default=False, label=_('Enable SMS'))
    SMS_TEST_PHONE = serializers.CharField(max_length=256, required=False, label=_('Test phone'))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['SMS_BACKEND'] = self.fields['SMS_BACKEND'].default
        return data


class AlibabaSMSSettingSerializer(BaseSMSSettingSerializer):
    SMS_BACKEND = serializers.ChoiceField(choices=BACKENDS.choices, default=BACKENDS.ALIBABA)
    ALIBABA_ACCESS_KEY_ID = serializers.CharField(max_length=256, required=True, label='AccessKeyId')
    ALIBABA_ACCESS_KEY_SECRET = serializers.CharField(
        max_length=256, required=False, label='AccessKeySecret', write_only=True)
    ALIBABA_SMS_SIGN_AND_TEMPLATES = serializers.DictField(
        label=_('Signatures and Templates'), required=True, help_text=_('''
        Filling in JSON Data: 
        {
            "verification_code": {
                "sign_name": "<Your signature name>", 
                "template_code": "<Your template code>"
            }
        }
        ''')
    )


class TencentSMSSettingSerializer(BaseSMSSettingSerializer):
    SMS_BACKEND = serializers.ChoiceField(choices=BACKENDS.choices, default=BACKENDS.TENCENT)
    TENCENT_SECRET_ID = serializers.CharField(max_length=256, required=True, label='Secret id')
    TENCENT_SECRET_KEY = serializers.CharField(max_length=256, required=False, label='Secret key', write_only=True)
    TENCENT_SDKAPPID = serializers.CharField(max_length=256, required=True, label='SDK app id')
    TENCENT_SMS_SIGN_AND_TEMPLATES = serializers.DictField(
        label=_('Signatures and Templates'), required=True, help_text=_('''
        Filling in JSON Data: 
        {
            "verification_code": {
                "sign_name": "<Your signature name>", 
                "template_code": "<Your template code>"
            }
        }
        '''))
