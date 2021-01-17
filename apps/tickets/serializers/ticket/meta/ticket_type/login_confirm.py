
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


__all__ = [
    'ApplySerializer', 'LoginConfirmSerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_login_ip = serializers.IPAddressField(
        required=True, label=_('Login ip'), allow_null=True
    )
    apply_login_city = serializers.CharField(
        required=True, max_length=64, label=_('Login city'), allow_null=True
    )
    apply_login_datetime = serializers.DateTimeField(
        required=True, label=_('Login datetime'), allow_null=True
    )


class LoginConfirmSerializer(ApplySerializer):
    pass
