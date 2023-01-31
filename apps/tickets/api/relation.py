from rest_framework import views
from rest_framework import status
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin

from orgs.utils import tmp_to_root_org
from common.api import JMSGenericViewSet
from terminal.serializers import SessionSerializer
from tickets.models import TicketSession
from tickets.serializers import TicketSessionRelationSerializer


class TicketSessionRelationViewSet(CreateModelMixin, JMSGenericViewSet):
    queryset = TicketSession.objects.all()
    serializer_class = TicketSessionRelationSerializer


# Todo: 放到上面的 ViewSet 中
class TicketSessionApi(views.APIView):
    perm_model = TicketSession
    rbac_perms = {
        '*': ['tickets.view_ticket']
    }

    def get(self, request, *args, **kwargs):
        with tmp_to_root_org():
            tid = self.kwargs['ticket_id']
            ticket_session = TicketSession.objects.filter(ticket=tid).first()
            if not ticket_session:
                return Response(status=status.HTTP_404_NOT_FOUND)

            session = ticket_session.session
            serializer = SessionSerializer(session)
            return Response(serializer.data)
