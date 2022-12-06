from rest_framework.decorators import action
from rest_framework.response import Response

from common.utils import reverse
from orgs.mixins.api import OrgBulkModelViewSet
from .. import models, serializers

__all__ = ['CommandFilterACLViewSet', 'CommandGroupViewSet']


class CommandGroupViewSet(OrgBulkModelViewSet):
    model = models.CommandGroup
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.CommandGroupSerializer


class CommandFilterACLViewSet(OrgBulkModelViewSet):
    model = models.CommandFilterACL
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.CommandFilterACLSerializer
    rbac_perms = {
        'command_review': 'tickets.add_superticket'
    }

    @action(['POST'], detail=False, url_path='command-review')
    def command_review(self, request, *args, **kwargs):
        serializer = serializers.CommandReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = {
            'run_command': serializer.validated_data['run_command'],
            'session': serializer.session,
            'cmd_filter_acl': serializer.cmd_filter_acl,
            'org_id': serializer.org.id
        }
        ticket = serializer.cmd_filter_acl.create_command_review_ticket(**data)

        url_review_status = reverse(
            view_name='api-tickets:super-ticket-status', kwargs={'pk': str(ticket.id)}
        )
        url_ticket_detail = reverse(
            view_name='api-tickets:ticket-detail', kwargs={'pk': str(ticket.id)},
            external=True, api_to_ui=True
        )
        resp_data = {
            'check_review_status': {'method': 'GET', 'url': url_review_status},
            'close_review': {'method': 'DELETE', 'url': url_review_status},
            'ticket_detail_url': url_ticket_detail,
            'reviewers': [
                str(ticket_assignee.assignee)
                for ticket_assignee in ticket.current_step.ticket_assignees.all()
            ]
        }
        return Response(resp_data)
