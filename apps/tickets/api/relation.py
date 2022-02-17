from rest_framework.mixins import CreateModelMixin
from rest_framework import views
from rest_framework.response import Response
from rest_framework import status

from common.drf.api import JMSGenericViewSet
from tickets.models import TicketSession
from tickets.serializers import TicketSessionRelationSerializer
from terminal.serializers import SessionSerializer
from orgs.utils import tmp_to_root_org


class TicketSessionRelationViewSet(CreateModelMixin, JMSGenericViewSet):
    queryset = TicketSession
    serializer_class = TicketSessionRelationSerializer


# Todo: 放到上面的 ViewSet 中
class TicketSessionApi(views.APIView):

    def get(self, request, *args, **kwargs):
        with tmp_to_root_org():
            ticketsession = TicketSession.objects.filter(ticket=self.kwargs['ticket_id']).first()
            if not ticketsession:
                return Response(status=status.HTTP_404_NOT_FOUND)

            session = ticketsession.session
            serializer = SessionSerializer(session)
            return Response(serializer.data)
