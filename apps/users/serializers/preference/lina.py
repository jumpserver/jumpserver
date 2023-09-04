from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField


class BasicSerializer(serializers.Serializer):
    secret_key = EncryptedField(
        required=False, max_length=1024,
        write_only=True, allow_blank=True, label=_('Secret Key')
    )
    secret_key_again = EncryptedField(
        required=False, max_length=1024,
        write_only=True, allow_blank=True, label=_('Secret Key Again')
    )

    def validate(self, attrs):
        secret_key = attrs.pop('secret_key', None)
        secret_key_again = attrs.pop('secret_key_again', None)

        if (secret_key or secret_key_again) and secret_key != secret_key_again:
            msg = _('The newly set password is inconsistent')
            raise serializers.ValidationError({'secret_key_again': msg})
        elif secret_key and secret_key_again:
            attrs['secret_key'] = secret_key
        return attrs


class LinaSerializer(serializers.Serializer):
    basic = BasicSerializer(required=False, label=_('Basic'))
