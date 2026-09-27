# -*- coding: utf-8 -*-
#
from django.conf import settings

from common.utils import get_logger
from .notifications import (
    TicketAppliedToAssigneeMessage, TicketProcessedToApplicantMessage,
    TicketUpdatedToCcUserMessage
)

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


def send_ticket_processed_mail_to_beneficiaries(ticket, processor):
    from .notifications import TicketProcessedToBeneficiaryMessage
    users = ticket.beneficiaries.exclude(user_id=ticket.applicant_id).exclude(
        user_id__in=ticket.cc_users.values_list('id', flat=True)
    ).select_related('user')
    for beneficiary in users:
        TicketProcessedToBeneficiaryMessage(beneficiary.user, ticket, processor).publish_async()


def send_ticket_updated_mail_to_cc_users(ticket):
    cc_users = ticket.cc_users.exclude(id=ticket.applicant_id)
    if not cc_users:
        return

    for user in cc_users:
        instance = TicketUpdatedToCcUserMessage(user, ticket)
        if settings.DEBUG:
            logger.debug(instance)
        instance.publish_async()
