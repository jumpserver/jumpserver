from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema_serializer
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
    relogin_required = serializers.BooleanField(
        required=False,
        help_text='Only present for relogin. False allows reuse of the recent login; true requires a new login.',
    )


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
        help_text='Maximum confirmation validity in seconds; relogin is measured from login, not confirmation.',
    )
    confirm_url = serializers.CharField(required=False, help_text='Endpoint for discovering and submitting confirmation.')


CONFIRMATION_REQUIRED_RESPONSE = OpenApiResponse(
    response=ConfirmationRequiredSerializer,
    description=(
        'Confirm the current operator using the type in code, then retry with the same session cookie. '
        'reason distinguishes missing confirmation, a different user, insufficient level and expiry. '
        'confirm_ttl is the maximum confirmation window, not the remaining session lifetime. '
        'MFA uses SECURITY_MFA_VERIFY_TTL (default 3600 seconds); password confirmation defaults to '
        '300 seconds. Relogin can only reuse the remaining portion of the first 300 seconds after '
        'the original Session authentication; recording confirmation never extends that deadline.'
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
        'or an incorrect password/MFA code returns an error message. Relogin outside the recent-login '
        'window returns code=relogin_required. No confirmation is recorded.'
    ),
)
