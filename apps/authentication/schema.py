from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema_serializer
from rest_framework import serializers

from .const import ConfirmType


class ConfirmationMethodSerializer(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField()
    disabled = serializers.BooleanField()
    placeholder = serializers.CharField()


@extend_schema_serializer(many=False)
class ConfirmationOptionsSerializer(serializers.Serializer):
    confirm_type = serializers.ChoiceField(choices=ConfirmType.choices)
    content = ConfirmationMethodSerializer(many=True)


class ConfirmationRequiredSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['user_confirm_required'])
    code = serializers.ChoiceField(choices=ConfirmType.choices, help_text='Required confirmation type.')
    detail = serializers.CharField(help_text='Reason and instructions for confirming the current user.')
    reason = serializers.ChoiceField(
        required=False,
        choices=['missing_confirmation', 'user_mismatch', 'insufficient_confirmation', 'confirmation_expired'],
    )
    confirm_ttl = serializers.IntegerField(
        required=False,
        help_text='Validity in seconds of a new confirmation of the required type, subject to session expiry.',
    )
    confirm_url = serializers.CharField(required=False, help_text='Endpoint for discovering and submitting confirmation.')
    purpose = serializers.CharField(required=False, help_text='Present for a purpose-specific confirmation requirement.')


CONFIRMATION_REQUIRED_RESPONSE = OpenApiResponse(
    response=ConfirmationRequiredSerializer,
    description=(
        'Confirm the current operator using the type in code, then retry with the same session cookie. '
        'reason distinguishes missing confirmation, a different user, insufficient level and expiry. '
        'confirm_ttl is the validity of a new confirmation, not the remaining session lifetime. '
        'MFA uses SECURITY_MFA_VERIFY_TTL (default 3600 seconds); ordinary password/relogin confirmation '
        'defaults to 300 seconds. Purpose-specific confirmation may have its own lifetime.'
    ),
    examples=[OpenApiExample(
        'Password confirmation does not satisfy MFA',
        value={
            'type': 'user_confirm_required',
            'code': 'mfa',
            'detail': 'The current confirmation does not meet the required level. '
                      'Confirm the current user with mfa, then retry with the same session cookie. '
                      'This confirmation is valid for 3600 seconds while the session remains valid.',
            'reason': 'insufficient_confirmation',
            'confirm_ttl': 3600,
            'confirm_url': '/api/v1/authentication/confirm/',
        },
    )],
)

CONFIRMATION_OK_RESPONSE = OpenApiResponse(
    response={'type': 'string', 'enum': ['ok']}, description='Confirmation succeeded.',
)

CONFIRMATION_BAD_REQUEST_RESPONSE = OpenApiResponse(
    response={'type': 'object'},
    description=(
        'Invalid or missing parameters return field-specific errors. An unavailable confirmation backend '
        'or an incorrect password/MFA code returns an error message. No confirmation is recorded.'
    ),
)

CONFIRMATION_PURPOSE_PARAMETER = OpenApiParameter(
    name='purpose', enum=['lock_password'],
    description='Use lock_password only when confirming a lock-password change.',
)
