from rest_framework import serializers

from common.drf.fields import EncryptedField
from ..const import ConfirmType


class ConfirmSerializer(serializers.Serializer):
    confirm_type = serializers.ChoiceField(
        required=True, choices=ConfirmType.choices
    )
    secret_key = EncryptedField()
