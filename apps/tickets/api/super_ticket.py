from rest_framework.generics import RetrieveDestroyAPIView

from orgs.utils import tmp_to_root_org
from ..serializers import SuperTicketSerializer
from ..models import Ticket


__all__ = ['SuperTicketStatusAPI']


class SuperTicketStatusAPI(RetrieveDestroyAPIView):
    serializer_class = SuperTicketSerializer
    rbac_perms = {
        'GET': 'tickets.view_superticket',
        'DELETE': 'tickets.change_superticket'
    }

    def get_queryset(self):
        with tmp_to_root_org():
            return Ticket.objects.all()

    def perform_destroy(self, instance):
        instance.close()
