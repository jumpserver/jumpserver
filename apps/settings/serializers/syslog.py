from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['SyslogSettingSerializer']


class SyslogSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Syslog')

    SYSLOG_ADDR = serializers.CharField(
        required=False, allow_blank=True, max_length=128,
        label=_('Syslog address'),
        help_text=_('Format: host:port, e.g. 192.168.0.1:514. Leave blank to disable syslog.')
    )
    SYSLOG_FACILITY = serializers.ChoiceField(
        required=False, allow_blank=True,
        choices=(
            ('kern', 'LOG_KERN'),
            ('user', 'LOG_USER'),
            ('mail', 'LOG_MAIL'),
            ('daemon', 'LOG_DAEMON'),
            ('auth', 'LOG_AUTH'),
            ('lpr', 'LOG_LPR'),
            ('news', 'LOG_NEWS'),
            ('uucp', 'LOG_UUCP'),
            ('cron', 'LOG_CRON'),
            ('authpriv', 'LOG_AUTHPRIV'),
            ('ftp', 'LOG_FTP'),
            ('syslog', 'LOG_SYSLOG'),
            ('local0', 'LOG_LOCAL0'),
            ('local1', 'LOG_LOCAL1'),
            ('local2', 'LOG_LOCAL2'),
            ('local3', 'LOG_LOCAL3'),
            ('local4', 'LOG_LOCAL4'),
            ('local5', 'LOG_LOCAL5'),
            ('local6', 'LOG_LOCAL6'),
            ('local7', 'LOG_LOCAL7'),
        ),
        label=_('Syslog facility'),
        help_text=_('Syslog facility type')
    )
    SYSLOG_SOCKTYPE = serializers.ChoiceField(
        required=False, allow_blank=True,
        choices=(
            (1, _('TCP')),
            (2, _('UDP')),
        ),
        label=_('Syslog socket type'),
        help_text=_('TCP or UDP protocol for syslog')
    )
