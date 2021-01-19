from django.utils.translation import ugettext as _
from tickets.models import Ticket


__all__ = ['DefaultPermissionName', 'get_default_permission_name']


def get_default_permission_name(ticket):
    name = ''
    if isinstance(ticket, Ticket):
        name = _('Created by ticket ({}-{})').format(ticket.title, str(ticket.id)[:4])
    return name


class DefaultPermissionName(object):
    default = None

    @staticmethod
    def _construct_default_permission_name(serializer_field):
        permission_name = ''
        ticket = serializer_field.root.instance
        if isinstance(ticket, Ticket):
            permission_name = get_default_permission_name(ticket)
        return permission_name

    def set_context(self, serializer_field):
        self.default = self._construct_default_permission_name(serializer_field)

    def __call__(self):
        return self.default
