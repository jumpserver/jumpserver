from rest_framework import serializers

from common.drf.fields import EncryptedField
from ..const import ConfirmType, MFAType


class ConfirmSerializer(serializers.Serializer):
    mfa_type = serializers.ChoiceField(
        required=False, allow_blank=True, choices=MFAType.choices
    )
    secret_key = EncryptedField()
