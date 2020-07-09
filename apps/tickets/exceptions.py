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
    pass


class TicketActionAlready(JMSException):
    pass


class OrgIdRequiredException(JMSException):
    pass
