from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['SyslogSettingSerializer']


class SyslogSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Syslog')

    SYSLOG_HOST = serializers.CharField(
        required=True, allow_blank=True, max_length=128,
        label=_('Syslog host'),
        help_text=_('Syslog server IP or hostname')
    )
    SYSLOG_PORT = serializers.IntegerField(
        required=True, min_value=1, max_value=65535,
        label=_('Syslog port'),
        help_text=_('Syslog server port, default 514')
    )
    SYSLOG_FACILITY = serializers.ChoiceField(
        required=True, allow_blank=True,
        choices=(
            ('kern', 'kern'),
            ('user', 'user'),
            ('mail', 'mail'),
            ('daemon', 'daemon'),
            ('auth', 'auth'),
            ('lpr', 'lpr'),
            ('news', 'news'),
            ('uucp', 'uucp'),
            ('cron', 'cron'),
            ('authpriv', 'authpriv'),
            ('ftp', 'ftp'),
            ('syslog', 'syslog'),
            ('local0', 'local0'),
            ('local1', 'local1'),
            ('local2', 'local2'),
            ('local3', 'local3'),
            ('local4', 'local4'),
            ('local5', 'local5'),
            ('local6', 'local6'),
            ('local7', 'local7'),
        ),
        label=_('Syslog facility'),
        help_text=_('Syslog facility type')
    )
    SYSLOG_SOCKTYPE = serializers.ChoiceField(
        required=True, allow_blank=True,
        choices=(
            (1, _('TCP')),
            (2, _('UDP')),
        ),
        label=_('Syslog socket type'),
        help_text=_('TCP or UDP protocol for syslog')
    )
