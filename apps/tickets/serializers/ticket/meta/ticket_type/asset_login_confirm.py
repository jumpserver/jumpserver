from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

__all__ = [
    'ApplySerializer', 'AssetLoginConfirmSerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_login_asset_ip = serializers.IPAddressField(
        required=True, label=_('Login Asset ip'), allow_null=True
    )
    apply_sys_username = serializers.CharField(
        required=True, max_length=64, label=_('System username'), allow_null=True
    )
    apply_login_datetime = serializers.DateTimeField(
        required=True, label=_('Login datetime'), allow_null=True
    )


class AssetLoginConfirmSerializer(ApplySerializer):
    pass
