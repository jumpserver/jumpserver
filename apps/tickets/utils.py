# -*- coding: utf-8 -*-
#
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response

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


class TicketLockManager:
    PROCESSING_TICKET_IDS = 'processing_ticket_ids'
    TICKET_LOCK_TIMEOUT = 60

    def __init__(self, ticket_id):
        self.ticket_id = ticket_id
        self.redis_client = cache.client.get_client()

    def acquire_lock(self):
        result = self.redis_client.sadd(self.PROCESSING_TICKET_IDS, self.ticket_id)

        if result == 0:
            return False

        self.redis_client.expire(self.PROCESSING_TICKET_IDS, self.TICKET_LOCK_TIMEOUT)

        return True

    def release_lock(self):
        self.redis_client.srem(self.PROCESSING_TICKET_IDS, self.ticket_id)

    def is_free(self):
        return self.acquire_lock()


def ticket_lock(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        ticket = self.get_object()
        lock_manager = TicketLockManager(str(ticket.id))

        if ticket.is_status(ticket.Status.closed):
            return Response({'detail': 'This ticket is closed'}, status=400)

        if not lock_manager.is_free():
            return Response({'detail': 'This ticket is already being processed.'}, status=400)

        try:
            self.check_permissions(request)
            return func(self, request, *args, **kwargs)
        finally:
            lock_manager.release_lock()

    return wrapper
