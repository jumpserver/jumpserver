from rest_framework import views
from rest_framework import status
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin

from orgs.models import Organization
from orgs.utils import tmp_to_root_org, tmp_to_org
from common.api import JMSGenericViewSet
from terminal.models import Session
from terminal.serializers import SessionSerializer
from tickets.models import Ticket, TicketSession
from tickets.serializers import TicketSessionRelationSerializer, TicketSessionSummarySerializer


class TicketSessionRelationViewSet(CreateModelMixin, JMSGenericViewSet):
    queryset = TicketSession.objects.all()
    serializer_class = TicketSessionRelationSerializer


# Todo: 放到上面的 ViewSet 中
class TicketSessionApi(views.APIView):
    perm_model = TicketSession
    rbac_perms = {
        '*': ['tickets.view_ticket']
    }

    @staticmethod
    def can_audit_org(user, org):
        if org is None:
            return False
        with tmp_to_org(org):
            # user.perms is cached for the request organization. Recompute
            # permissions in the session organization for audit access.
            return 'terminal.view_session' in user.get_all_permissions()

    def get(self, request, *args, **kwargs):
        with tmp_to_root_org():
            tid = self.kwargs['ticket_id']
            ticket_session = TicketSession.objects.filter(ticket=tid).first()
            if not ticket_session:
                return Response(status=status.HTTP_404_NOT_FOUND)

            session = ticket_session.session
            related = Ticket.get_user_related_tickets(request.user).filter(id=tid).exists()
            if not related and not self.can_audit_org(request.user, session.org):
                return Response(status=status.HTTP_404_NOT_FOUND)
            serializer = SessionSerializer(session)
            return Response(serializer.data)


class TicketSessionListApi(TicketSessionApi):
    def get(self, request, ticket_id):
        with tmp_to_root_org():
            sessions = Session.objects.filter(ticket_relation__ticket_id=ticket_id)
            if not Ticket.get_user_related_tickets(request.user).filter(pk=ticket_id).exists():
                org_ids = sessions.order_by().values_list('org_id', flat=True).distinct()
                allowed = [oid for oid in org_ids if self.can_audit_org(request.user, Organization.get_instance(oid))]
                if not allowed:
                    return Response(status=status.HTTP_404_NOT_FOUND)
                sessions = sessions.filter(org_id__in=allowed)
            sessions = sessions.select_related('terminal').distinct().order_by('is_finished', 'date_start', 'id')
            return Response(TicketSessionSummarySerializer(sessions, many=True).data)
