from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['CertSettingSerializer']


class CertSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Certificate')

    AUTH_CERT = serializers.BooleanField(
        default=False, label=_('Certificate')
    )
