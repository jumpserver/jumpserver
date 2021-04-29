from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.generics import RetrieveDestroyAPIView

from common.permissions import IsAppUser
from common.utils import lazyproperty
from orgs.utils import tmp_to_root_org
from ..models import Ticket


__all__ = ['GenericTicketStatusRetrieveCloseAPI']


class GenericTicketStatusRetrieveCloseAPI(RetrieveDestroyAPIView):
    permission_classes = (IsAppUser, )

    def retrieve(self, request, *args, **kwargs):
        if self.ticket.action_open:
            status = 'await'
        elif self.ticket.action_approve:
            status = 'approve'
        else:
            status = 'reject'
        data = {
            'status': status,
            'action': self.ticket.action,
            'processor': self.ticket.processor_display
        }
        return Response(data=data, status=200)

    def destroy(self, request, *args, **kwargs):
        if self.ticket.status_open:
            self.ticket.close(processor=self.ticket.applicant)
        data = {
            'action': self.ticket.action,
            'status': self.ticket.status,
            'processor': self.ticket.processor_display
        }
        return Response(data=data, status=200)

    @lazyproperty
    def ticket(self):
        with tmp_to_root_org():
            return get_object_or_404(Ticket, pk=self.kwargs['pk'])
