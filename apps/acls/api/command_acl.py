from rest_framework.decorators import action
from rest_framework.response import Response

from orgs.mixins.api import OrgBulkModelViewSet
from .common import ACLUserAssetFilterMixin
from .. import models, serializers

__all__ = ['CommandFilterACLViewSet', 'CommandGroupViewSet']


class CommandGroupViewSet(OrgBulkModelViewSet):
    model = models.CommandGroup
    chat_ai_create_reuse = {
        'lookup_operation_id': 'acls_command_groups_list',
        'fields': [
            {
                'body_field': 'type',
                'query_parameter': 'type',
                'unwrap': 'value',
                'default': models.CommandGroup.TypeChoices.command,
            },
            {
                'body_field': 'content',
                'query_parameter': 'content',
            },
            {
                'body_field': 'ignore_case',
                'query_parameter': 'ignore_case',
                'default': True,
            },
        ],
    }
    filterset_fields = (
        'name', 'type', 'content', 'ignore_case', 'command_filters'
    )
    search_fields = ('name',)
    serializer_class = serializers.CommandGroupSerializer


class CommandACLFilter(ACLUserAssetFilterMixin):
    class Meta:
        model = models.CommandFilterACL
        fields = ['id', 'name', 'users', 'assets', 'action']


class CommandFilterACLViewSet(OrgBulkModelViewSet):
    model = models.CommandFilterACL
    filterset_class = CommandACLFilter
    search_fields = ['name']
    serializer_classes = {
        'default': serializers.CommandFilterACLSerializer,
        'list': serializers.CommandFilterACLListSerializer,
    }
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
        info = ticket.get_extra_info_of_review(user=request.user)
        return Response(data=info)
