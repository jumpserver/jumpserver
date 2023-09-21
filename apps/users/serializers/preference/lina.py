from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from ...models import Preference


class BasicSerializer(serializers.Serializer):
    has_secret_key = serializers.SerializerMethodField()
    secret_key = EncryptedField(
        required=False, max_length=1024,
        write_only=True, allow_blank=True,
        label=_('New file encryption password')
    )
    secret_key_again = EncryptedField(
        required=False, max_length=1024,
        write_only=True, allow_blank=True,
        label=_('Confirm file encryption password')
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


class LinaSerializer(serializers.Serializer):
    basic = BasicSerializer(required=False, label=_('Basic'))
