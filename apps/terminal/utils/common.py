# -*- coding: utf-8 -*-
#

from common.utils import get_logger
from tickets.models import TicketSession

logger = get_logger(__name__)


def is_session_approver(session_id, user_id):
    ticket = TicketSession.get_ticket_by_session_id(session_id)
    if not ticket:
        return False
    ok = ticket.has_all_assignee(user_id)
    return ok
