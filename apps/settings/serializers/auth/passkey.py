from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['PasskeySettingSerializer']


class PasskeySettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Passkey')

    AUTH_PASSKEY = serializers.BooleanField(
        default=False, label=_('Passkey'),
        help_text=_('Only SSL domain can use passkey auth')
    )
    FIDO_SERVER_ID = serializers.CharField(
        max_length=255, label=_('FIDO Server ID'), required=False, allow_blank=True,
        help_text=_(
            'The hostname can using passkey auth, If not set, '
            'will use request host and the request host in DOMAINS, '
            'If multiple domains, use comma to separate'
        )
    )
    FIDO_SERVER_NAME = serializers.CharField(max_length=255, label=_('FIDO Server name'))
