from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.utils.mcp import get_mcp_authorization_server
from orgs.models import Organization


class BasicSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Basic')

    SITE_URL = serializers.URLField(
        required=True, label=_("Site URL"),
        help_text=_(
            'Site URL is the externally accessible address of the current product '
            'service and is usually used in links in system emails'
        )
    )
    USER_GUIDE_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("User guide url"),
        help_text=_('User first login update profile done redirect to it')
    )
    GLOBAL_ORG_DISPLAY_NAME = serializers.CharField(
        required=False, max_length=1024, allow_blank=True, allow_null=True, label=_("Global org display"),
        help_text=_('The name of global organization to display')
    )
    HELP_DOCUMENT_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("Document URL"),
        help_text=_('Document URL refers to the address in the top navigation bar Help - Document')
    )
    HELP_SUPPORT_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("Support URL"),
        help_text=_('Support URL refers to the address in the top navigation bar Help - Support')
    )

    @staticmethod
    def validate_SITE_URL(s):
        if not s:
            s = 'http://127.0.0.1'
        s = s.strip('/')
        if settings.MCP_ENABLED:
            try:
                get_mcp_authorization_server(s)
            except ImproperlyConfigured as exc:
                raise serializers.ValidationError(_('Agent MCP requires an HTTP or HTTPS Site URL.')) from exc
        return s

    @staticmethod
    def validate_GLOBAL_ORG_DISPLAY_NAME(s):
        org_names = Organization.objects.values_list('name', flat=True)
        if s in org_names:
            raise serializers.ValidationError(_('Organization name already exists'))
        return s
