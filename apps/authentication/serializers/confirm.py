from rest_framework import serializers

from common.serializers.fields import EncryptedField
from ..const import ConfirmType, MFAType


class ConfirmSerializer(serializers.Serializer):
    confirm_type = serializers.ChoiceField(required=True, allow_blank=True, choices=ConfirmType.choices)
    mfa_type = serializers.ChoiceField(required=False, allow_blank=True, choices=MFAType.choices)
    secret_key = EncryptedField(allow_blank=True, required=False)
