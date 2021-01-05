
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


__all__ = [
    'ApplySerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_login_ip = serializers.IPAddressField(
        required=True, label=_('Login ip')
    )
    apply_login_city = serializers.CharField(
        required=True, max_length=64, label=_('Login city')
    )
    apply_login_datetime = serializers.DateTimeField(
        required=True, label=_('Login datetime')
    )

