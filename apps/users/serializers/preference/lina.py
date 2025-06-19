from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.const import Language
from common.serializers.fields import EncryptedField
from ...models import Preference


class FileEncryptSerializer(serializers.Serializer):
    has_secret_key = serializers.SerializerMethodField(
        help_text=_(
            '*! The password for file encryption, '
            'used for decryption when the system sends emails containing file attachments. '
            '<br>'
            'Such as: account backup files, account password change results files'
        ),
    )
    secret_key = EncryptedField(
        required=False, max_length=1024,
        write_only=True, allow_blank=True,
        label=_('New password'),
    )
    secret_key_again = EncryptedField(
        required=False, max_length=1024,
        write_only=True, allow_blank=True,
        label=_('Confirm password')
    )

    def get_has_secret_key(self, obj):
        user = self.context['request'].user
        query = {'user': user, 'name': 'secret_key', 'category': 'lina'}
        return Preference.objects.filter(**query).exists()

    def validate(self, attrs):
        secret_key = attrs.pop('secret_key', None)
        secret_key_again = attrs.pop('secret_key_again', None)

        if (secret_key or secret_key_again) and secret_key != secret_key_again:
            msg = _('The newly set password is inconsistent')
            raise serializers.ValidationError({'secret_key_again': msg})
        elif secret_key and secret_key_again:
            attrs['secret_key'] = secret_key
        return attrs


class BasicSerializer(serializers.Serializer):
    lang = serializers.ChoiceField(required=False, choices=Language.choices, label=_('Language'), default=Language.en)


class LinaSerializer(serializers.Serializer):
    basic = BasicSerializer(required=False, label=_('Basic'))
    file = FileEncryptSerializer(required=False, label=_('File Encryption'))
