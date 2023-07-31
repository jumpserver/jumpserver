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
    TERMINAL_TELNET_REGEX = serializers.CharField(
        allow_blank=True, max_length=1024, required=False, label=_('Telnet login regex'),
        help_text=_("Tips: The login success message varies with devices. "
                    "if you cannot log in to the device through Telnet, set this parameter")
    )
    TERMINAL_MAGNUS_ENABLED = serializers.BooleanField(label=_("Enable database proxy"))
    TERMINAL_RAZOR_ENABLED = serializers.BooleanField(label=_("Enable Razor"))
    TERMINAL_KOKO_SSH_ENABLED = serializers.BooleanField(label=_("Enable SSH Client"))

    RESOLUTION_CHOICES = (
        ('Auto', 'Auto'),
        ('1024x768', '1024x768'),
        ('1366x768', '1366x768'),
        ('1600x900', '1600x900'),
        ('1920x1080', '1920x1080')
    )
    TERMINAL_GRAPHICAL_RESOLUTION = serializers.ChoiceField(
        default='Auto', choices=RESOLUTION_CHOICES, required=False,
        label=_('Default graphics resolution'),
        help_text=_('Tip: Default resolution to use when connecting graphical assets in Luna pages')
    )
