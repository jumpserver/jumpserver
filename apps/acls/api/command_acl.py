from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from orgs.mixins.api import OrgBulkModelViewSet
from .common import ACLUserAssetFilterMixin
from .. import models, serializers
from ..notifications import AclWarnningMessage

__all__ = ['CommandFilterACLViewSet', 'CommandGroupViewSet']


class CommandGroupViewSet(OrgBulkModelViewSet):
    model = models.CommandGroup
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.CommandGroupSerializer


class CommandACLFilter(ACLUserAssetFilterMixin):
    class Meta:
        model = models.CommandFilterACL
        fields = ['name', ]


class CommandFilterACLViewSet(OrgBulkModelViewSet):
    model = models.CommandFilterACL
    filterset_class = CommandACLFilter
    search_fields = ['name']
    serializer_class = serializers.CommandFilterACLSerializer
    rbac_perms = {
        'command_review': 'tickets.add_superticket',
        'command_warnning': 'tickets.add_superticket'
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

    @action(['POST'], detail=False, url_path='command-warnning')
    def command_warnning(self, request, *args, **kwargs):
        serializer = serializers.CommandWarnningSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewers = serializer.cmd_filter_acl.reviewers.all()
        context = {
            'run_command': serializer.validated_data['run_command'],
            'cmd_filter_acl': serializer.cmd_filter_acl.id,
            'session_id': serializer.session.id,
            'asset': serializer.asset,
            'account': serializer.session.account,
            'org_id': serializer.org.id
        }
        for user in reviewers:
            AclWarnningMessage(user, context).publish_async()
        return Response({'detail': 'ok'})
