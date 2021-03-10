from django.utils.translation import ugettext as _

common_help_text = _('Format for comma-delimited string, with `*` indicating a match all. \n')

ip_group_help_text = common_help_text + _(
    'IP range. Such as: '
    '192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64. \n'
)
