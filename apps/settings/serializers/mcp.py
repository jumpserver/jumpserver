from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.validators import validate_mcp_resource_url

__all__ = ['MCPSettingSerializer']


class MCPSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Agent / MCP')

    # Persist the address before enabling discovery when both settings change.
    MCP_PUBLIC_URL = serializers.CharField(
        required=False, allow_blank=True, max_length=512, trim_whitespace=False,
        label=_('MCP access URL'), validators=[validate_mcp_resource_url],
        help_text=_('The external HTTP or HTTPS MCP URL. Koko retrieves updates every 60 seconds. '
                    'Clearing this address stops new MCP requests.'),
    )
    MCP_DCR_ENABLED = serializers.BooleanField(
        required=False, label=_('Allow automatic client registration'),
        help_text=_(
            'Allow clients to register automatically before users log in and authorize access. '
            'Disabling this stops new client registrations without revoking existing authorizations.'
        ),
    )

    def validate(self, attrs):
        enabled = attrs.get('MCP_DCR_ENABLED', settings.MCP_DCR_ENABLED)
        resource = attrs.get('MCP_PUBLIC_URL', settings.MCP_PUBLIC_URL)
        if enabled:
            if not resource:
                raise serializers.ValidationError({'MCP_PUBLIC_URL': _('This field is required when registration is enabled.')})
            # A partial update must also validate the existing deployment value.
            try:
                validate_mcp_resource_url(resource)
            except ValidationError as exc:
                raise serializers.ValidationError({'MCP_PUBLIC_URL': exc.messages}) from exc
        attrs = super().validate(attrs)
        if attrs.get('MCP_DCR_ENABLED') is False:
            # Disable discovery before a cleared URL is applied by subscribers.
            return {'MCP_DCR_ENABLED': False, **attrs}
        return attrs
