from common.exceptions import JmsException


class NotHaveConfirmedAssets(JmsException):
    pass


class ConfirmedAssetsChanged(JmsException):
    pass


class NotHaveConfirmedSystemUser(JmsException):
    pass


class ConfirmedSystemUserChanged(JmsException):
    pass


class TicketClosed(JmsException):
    pass


class TicketActionYet(JmsException):
    pass
