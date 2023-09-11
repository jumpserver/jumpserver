from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class TerminalSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Terminal')

    SORT_BY_CHOICES = (
        ('name', _('Hostname')),
        ('ip', _('IP'))
    )

    PAGE_SIZE_CHOICES = (
        ('all', _('All')),
        ('auto', _('Auto')),
        ('10', '10'),
        ('15', '15'),
        ('25', '25'),
        ('50', '50'),
    )
    SECURITY_SERVICE_ACCOUNT_REGISTRATION = serializers.BooleanField(
        required=True, label=_('Enable terminal register'),
        help_text=_(
            "Allow terminal register, after all terminal setup, you should disable this for security"
        )
    )
    TERMINAL_PASSWORD_AUTH = serializers.BooleanField(required=False, label=_('Password auth'))
    TERMINAL_PUBLIC_KEY_AUTH = serializers.BooleanField(
        required=False, label=_('Public key auth'),
        help_text=_('Tips: If use other auth method, like AD/LDAP, you should disable this to '
                    'avoid being able to log in after deleting')
    )
    TERMINAL_ASSET_LIST_SORT_BY = serializers.ChoiceField(
        SORT_BY_CHOICES, required=False, label=_('List sort by')
    )
    TERMINAL_ASSET_LIST_PAGE_SIZE = serializers.ChoiceField(
        PAGE_SIZE_CHOICES, required=False, label=_('List page size')
    )
    TERMINAL_MAGNUS_ENABLED = serializers.BooleanField(label=_("Enable database proxy"))
    TERMINAL_RAZOR_ENABLED = serializers.BooleanField(label=_("Enable Razor"))
    TERMINAL_KOKO_SSH_ENABLED = serializers.BooleanField(label=_("Enable SSH Client"))
