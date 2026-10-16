from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'login_confirm'
    label = _('Login confirm')
    allow_global = True
    global_options_permission = 'acls.change_loginacl'
    execution_mode = 'external'

    def build_context(self, ticket):
        data = ticket.request_data
        return {'request': {'ip': data.get('apply_login_ip'), 'city': data.get('apply_login_city'),
                            'datetime': data.get('apply_login_datetime')}}

    def request_items(self, ticket):
        data = ticket.request_data
        instance = getattr(ticket, 'workflow_instance', None)
        requested = instance.context.get('request', {}) if instance else {}
        return [
            {'name': 'apply_login_ip', 'label': str(_('Login IP')), 'value': requested.get('ip', data.get('apply_login_ip'))},
            {'name': 'apply_login_city', 'label': str(_('Login city')), 'value': requested.get('city', data.get('apply_login_city'))},
            {'name': 'apply_login_datetime', 'label': str(_('Login Date')), 'value': requested.get('datetime', data.get('apply_login_datetime'))},
        ]
