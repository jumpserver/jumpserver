# -*- coding: utf-8 -*-
#
from django.conf import settings

from common.utils import get_logger
from .notifications import TicketAppliedToAssigneeMessage, TicketProcessedToApplicantMessage

logger = get_logger(__file__)


def send_ticket_applied_mail_to_assignees(ticket, assignees):
    if not assignees:
        logger.debug(
            "Not found assignees, ticket: {}({}), assignees: {}".format(
                ticket, str(ticket.id), assignees
            )
        )
        return

    for user in assignees:
        instance = TicketAppliedToAssigneeMessage(user, ticket)
        if settings.DEBUG:
            logger.debug(instance)
        instance.publish_async()


def send_ticket_processed_mail_to_applicant(ticket, processor):
    if not ticket.applicant:
        logger.error("Not found applicant: {}({})".format(ticket.title, ticket.id))
        return

    instance = TicketProcessedToApplicantMessage(ticket.applicant, ticket, processor)
    if settings.DEBUG:
        logger.debug(instance)
    instance.publish_async()
