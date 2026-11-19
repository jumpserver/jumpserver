from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from ..const import ConfirmType, MFAType


class ConfirmQuerySerializer(serializers.Serializer):
    confirm_type = serializers.ChoiceField(choices=ConfirmType.choices, default=ConfirmType.PASSWORD)


class ConfirmSerializer(serializers.Serializer):
    confirm_type = serializers.ChoiceField(
        choices=ConfirmType.choices,
        help_text=_("Confirmation type returned by GET /api/v1/authentication/confirm/."),
    )
    mfa_type = serializers.ChoiceField(
        required=False, allow_blank=True, choices=MFAType.choices,
        help_text=_("Required for MFA confirmation. Select an enabled method of the current user, such as otp."),
    )
    secret_key = EncryptedField(
        allow_blank=True, required=False,
        help_text=_("Current user's password or MFA code. Required for password and code-based MFA confirmation."),
    )

    def validate(self, attrs):
        errors = {}
        if attrs['confirm_type'] == ConfirmType.MFA and not attrs.get('mfa_type'):
            errors['mfa_type'] = _("This field is required for MFA confirmation.")
        if attrs['confirm_type'] == ConfirmType.PASSWORD and not attrs.get('secret_key'):
            errors['secret_key'] = _("This field is required for password confirmation.")
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
