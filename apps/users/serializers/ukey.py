from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from ..models import UKey


class UKeySerializer(serializers.ModelSerializer):
    u_key_public_key = EncryptedField(write_only=True, label=_("USB Key Public Key"))

    class Meta:
        model = UKey
        read_only_fields = ['date_created', 'date_updated']
        fields = ['id', 'user', 'u_key_serial', 'u_key_public_key'] + read_only_fields
