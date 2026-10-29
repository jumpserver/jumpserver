from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.validators import validate_mcp_resource_url
from common.utils.mcp import get_mcp_authorization_server

__all__ = ['MCPSettingSerializer']


class MCPSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Agent / MCP')

    # Persist the address before enabling the service when both settings change.
    MCP_PUBLIC_URL = serializers.CharField(
        required=False, allow_blank=True, max_length=512, trim_whitespace=False,
        label=_('MCP access URL'), validators=[validate_mcp_resource_url],
        help_text=_('The external HTTP or HTTPS MCP URL. Koko retrieves updates every 60 seconds. '
                    'Disable MCP access before clearing this address.'),
    )
    MCP_ENABLED = serializers.BooleanField(
        required=False, label=_('Enable MCP access'),
        help_text=_(
            'Koko retrieves this setting every 60 seconds. Disabling stops new MCP requests '
            'while accepted operations and audit delivery finish. The authorization address uses the Site URL.'
        ),
    )
    MCP_DCR_ENABLED = serializers.BooleanField(
        required=False, label=_('Allow automatic client registration'),
        help_text=_(
            'Allow clients to register automatically before users log in and authorize access. '
            'This takes effect only while MCP access is enabled. Disabling stops new client '
            'registrations without revoking existing authorizations.'
        ),
    )

    def validate(self, attrs):
        enabled = attrs.get('MCP_ENABLED', settings.MCP_ENABLED)
        resource = attrs.get('MCP_PUBLIC_URL', settings.MCP_PUBLIC_URL)
        if enabled:
            if not resource:
                raise serializers.ValidationError({'MCP_PUBLIC_URL': _('This field is required when MCP access is enabled.')})
            # A partial update must also validate the existing deployment value.
            try:
                validate_mcp_resource_url(resource)
            except ValidationError as exc:
                raise serializers.ValidationError({'MCP_PUBLIC_URL': exc.messages}) from exc
            try:
                get_mcp_authorization_server(attrs.get('SITE_URL', settings.SITE_URL))
            except ImproperlyConfigured as exc:
                raise serializers.ValidationError({'MCP_ENABLED': _('Configure a valid HTTP or HTTPS Site URL in Basic settings first.')}) from exc
        attrs = super().validate(attrs)
        if attrs.get('MCP_ENABLED') is False:
            # Stop discovery before a cleared URL is applied by subscribers.
            return {'MCP_ENABLED': False, **attrs}
        return attrs
