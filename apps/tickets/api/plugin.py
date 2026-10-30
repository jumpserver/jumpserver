from django.utils.translation import gettext
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
            raise ValidationError({'org_id': gettext('Select a concrete organization.')})
        if not available_users(org_id).filter(pk=request.user.pk).exists():
            raise PermissionDenied()
        with tmp_to_org(org_id):
            if request.query_params.get('field') == 'availability':
                from tickets.workflow.resources import resource_availability
                return Response(resource_availability(get_ticket_plugin(pk), request, org_id))
            return Response(get_ticket_plugin(pk).options(request, org_id))

    @action(detail=True, methods=['post'], url_path='upload-file')
    def upload_file(self, request, pk=None):
        from common.drf.throttling import FileTransferThrottle
        from tickets.plugins.file_transfer.storage import stage_upload
        if pk != 'file_transfer':
            raise ValidationError(gettext('This ticket type does not accept files.'))
        throttle = FileTransferThrottle()
        if not throttle.allow_request(request, self):
            self.throttled(request, throttle.wait())
        org_id = str(request.data.get('org_id', current_org.id))
        if org_id == Organization.ROOT_ID or not Organization.objects.filter(pk=org_id).exists():
            raise ValidationError(gettext('Select a concrete organization.'))
        if not available_users(org_id).filter(pk=request.user.pk).exists():
            raise PermissionDenied()
        files = request.FILES.getlist('file')
        if len(files) != 1:
            raise ValidationError(gettext('Upload one file at a time.'))
        with tmp_to_org(org_id):
            record = stage_upload(request.user, org_id, files[0])
        return Response(record.summary(), status=201)
