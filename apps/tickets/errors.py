# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import status

from common.exceptions import JMSException


class TicketStateChanged(JMSException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'ticket_state_changed'
    default_detail = _(
        "The ticket status has changed. Please refresh the page and try again."
    )


class AlreadyClosed(TicketStateChanged):
    default_code = 'ticket_already_processed'
