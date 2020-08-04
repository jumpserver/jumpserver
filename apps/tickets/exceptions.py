from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException


class NotHaveConfirmedAssets(JMSException):
    pass


class ConfirmedAssetsChanged(JMSException):
    pass


class NotHaveConfirmedSystemUser(JMSException):
    pass


class ConfirmedSystemUserChanged(JMSException):
    pass


class TicketClosed(JMSException):
    default_detail = _('Ticket closed')
    default_code = 'ticket_closed'


class TicketActionAlready(JMSException):
    pass


class OnlyTicketAssigneeCanOperate(JMSException):
    default_detail = _('Only assignee can operate ticket')
    default_code = 'can_not_operate'


class TicketCanNotOperate(JMSException):
    default_detail = _('Ticket can not be operated')
    default_code = 'ticket_can_not_be_operated'
