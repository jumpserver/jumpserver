from rest_framework.generics import RetrieveDestroyAPIView

from orgs.utils import tmp_to_root_org
from ..serializers import SuperTicketSerializer
from ..models import SuperTicket


__all__ = ['SuperTicketStatusAPI']


class SuperTicketStatusAPI(RetrieveDestroyAPIView):
    serializer_class = SuperTicketSerializer

    def get_queryset(self):
        with tmp_to_root_org():
            return SuperTicket.objects.all()

    def perform_destroy(self, instance):
        ticket = self.get_object()
        ticket.close(processor=ticket.applicant)
