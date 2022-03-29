from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class TerminalSettingSerializer(serializers.Serializer):
    SORT_BY_CHOICES = (
        ('hostname', _('Hostname')),
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
        help_text=_("The login success message varies with devices. "
                    "if you cannot log in to the device through Telnet, set this parameter")
    )
    TERMINAL_RDP_ADDR = serializers.CharField(
        required=False, label=_("RDP address"), max_length=1024, allow_blank=True,
        help_text=_('RDP visit address, eg: dev.jumpserver.org:3389')
    )
    XRDP_ENABLED = serializers.BooleanField(label=_("Enable XRDP"))

    TERMINAL_KOKO_HOST = serializers.BooleanField(label=_("Koko host"))
    TERMINAL_KOKO_SSH_PORT = serializers.BooleanField(label=_("Koko ssh port"))

    TERMINAL_MAGNUS_ENABLED = serializers.BooleanField(label=_("Enable database proxy"))
    TERMINAL_MAGNUS_HOST = serializers.CharField(
        required=False, label=_("Database proxy host"), max_length=1024, allow_blank=True,
        help_text=_('Database proxy host, eg: dev.jumpserver.org')
    )
    TERMINAL_MAGNUS_MYSQL_PORT = serializers.IntegerField(
        required=False, label=_("MySQL port"), default=33060,
        help_text=_('MySQL protocol listen port')
    )
    TERMINAL_MAGNUS_MARIADB_PORT = serializers.IntegerField(
        required=False, label=_("MariaDB port"), default=33061,
        help_text=_('MariaDB protocol listen port')
    )
    TERMINAL_MAGNUS_POSTGRE_PORT = serializers.IntegerField(
        required=False, label=_("PostgreSQL port"), default=54320,
        help_text=_('PostgreSQL protocol listen port')
    )

