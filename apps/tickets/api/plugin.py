from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from orgs.models import Organization
from orgs.utils import current_org, tmp_to_org
from tickets.plugins import get_ticket_plugin, ticket_plugins
from tickets.workflow.approvers import available_users


class TicketTypeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response([plugin.metadata() for plugin in ticket_plugins.all(visible=True)])

    @action(detail=True, methods=['get'], url_path='options')
    def resource_options(self, request, pk=None):
        org_id = request.query_params.get('org_id', str(current_org.id))
        if org_id == Organization.ROOT_ID or not Organization.objects.filter(pk=org_id).exists():
            raise ValidationError({'org_id': 'Select a concrete organization.'})
        if not available_users(org_id).filter(pk=request.user.pk).exists():
            raise PermissionDenied()
        with tmp_to_org(org_id):
            return Response(get_ticket_plugin(pk).options(request, org_id))
