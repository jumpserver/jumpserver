# -*- coding: utf-8 -*-
#
from django.conf import settings

from common.utils import get_logger
from .notifications import TicketAppliedToAssignee, TicketProcessedToApplicant

logger = get_logger(__file__)


def send_ticket_applied_mail_to_assignees(ticket):
    ticket_assignees = ticket.current_node.first().ticket_assignees.all()
    if not ticket_assignees:
        logger.debug(
            "Not found assignees, ticket: {}({}), assignees: {}".format(ticket, str(ticket.id), ticket_assignees)
        )
        return

    for ticket_assignee in ticket_assignees:
        instance = TicketAppliedToAssignee(ticket_assignee.assignee, ticket)
        if settings.DEBUG:
            logger.debug(instance)
        instance.publish_async()


def send_ticket_processed_mail_to_applicant(ticket, processor):
    if not ticket.applicant:
        logger.error("Not found applicant: {}({})".format(ticket.title, ticket.id))
        return

    instance = TicketProcessedToApplicant(ticket.applicant, ticket, processor)
    if settings.DEBUG:
        logger.debug(instance)
    instance.publish_async()
