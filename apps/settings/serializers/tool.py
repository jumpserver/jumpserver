from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = [
    'ToolSerializer'
]


class ToolSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Tool')

    TOOL_USER_ENABLED = serializers.BooleanField(
        label=_('Tools in the Workbench'), default=True,
        help_text=_(
            "*! If enabled, users with RBAC permissions will be able to utilize all "
            "tools in the workbench"
        )
    )