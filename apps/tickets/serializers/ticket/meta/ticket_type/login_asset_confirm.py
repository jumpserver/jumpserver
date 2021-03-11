
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


__all__ = [
    'ApplySerializer', 'LoginAssetConfirmSerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_login_user = serializers.CharField(required=True, label=_('Login user'))
    apply_login_asset = serializers.CharField(required=True, label=_('Login asset'))
    apply_login_system_user = serializers.CharField(
        required=True, max_length=64, label=_('Login system user')
    )


class LoginAssetConfirmSerializer(ApplySerializer):
    pass
