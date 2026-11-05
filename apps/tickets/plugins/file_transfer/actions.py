from django.utils.translation import gettext
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from rest_framework.response import Response

from common.drf.throttling import FileTransferThrottle
from common.utils import get_request_ip
from tickets.models import Ticket, TicketTransferFile, TicketTransferExecution, WorkflowInstance, ApprovalTask
from tickets.plugins.actions import TicketAction
from .execution import dispatch, event, get_result
from .policy import validate_context, path_module


def can_review(ticket, user):
    return bool(user and (user.pk == ticket.applicant_id or ApprovalTask.objects.filter(
        node_instance__instance=ticket.workflow_instance, assignee=user,
        state__in=['pending', 'approved', 'rejected'],
    ).exists()))


def file_response(record):
    try:
        response = FileResponse(record.path.open('rb'), as_attachment=True, filename=record.name,
                                content_type='application/octet-stream')
    except OSError as exc:
        raise NotFound(gettext('The file is no longer available.')) from exc
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def requested_file(ticket, request, kind):
    file_id = serializers.UUIDField().run_validation(request.query_params.get('file_id'))
    return get_object_or_404(TicketTransferFile, pk=file_id, ticket=ticket, org_id=ticket.org_id,
                             kind=kind, purged_at__isnull=True, expires_at__gt=timezone.now())


class ExecuteTransfer(TicketAction):
    throttle_classes = (FileTransferThrottle,)

    def execute(self, ticket, request):
        if request.data:
            raise ValidationError(gettext('Execution uses the approved files and paths; parameters cannot be changed.'))
        with transaction.atomic():
            WorkflowInstance.objects.select_for_update().get(ticket=ticket)
            ticket = Ticket.objects.select_related('workflow_instance', 'applicant').get(pk=ticket.pk)
            ip = get_request_ip(request)
            validate_context(ticket, approved=True, user=request.user, remote_addr=ip)
            context = ticket.workflow_instance.context
            paths = path_module(context['transfer_protocol'])
            if context['request']['direction'] == 'upload':
                files = [{**item, 'path': paths.join(context['request']['target_directory'], item['name']),
                          'state': 'pending'} for item in context['transfer_files']]
            else:
                files = [{'name': paths.basename(path), 'path': path, 'state': 'pending'}
                         for path in context['request']['paths']]
            _, created = TicketTransferExecution.objects.get_or_create(
                ticket=ticket, org_id=ticket.org_id, defaults={'files': files, 'remote_addr': ip},
            )
            if created:
                event(ticket, 'transfer.submitted')
                transaction.on_commit(lambda: dispatch(ticket.pk), robust=True)
        return Response(get_result(ticket, request.user), status=202)


class ReviewTransferFile(TicketAction):
    method = 'GET'
    throttle_classes = (FileTransferThrottle,)

    def execute(self, ticket, request):
        if ticket.workflow_instance.context.get('file_transfer_version') != 2 or not can_review(ticket, request.user):
            raise PermissionDenied(gettext('Only the applicant and assigned reviewers can inspect uploaded files.'))
        record = requested_file(ticket, request, 'upload')
        return file_response(record)


class DownloadTransferFile(TicketAction):
    method = 'GET'
    throttle_classes = (FileTransferThrottle,)

    def execute(self, ticket, request):
        validate_context(ticket, approved=True, user=request.user, remote_addr=get_request_ip(request))
        record = requested_file(ticket, request, 'download')
        execution = get_object_or_404(TicketTransferExecution, ticket=ticket, org_id=ticket.org_id)
        if not any(item.get('id') == str(record.pk) and item['state'] == 'success' for item in execution.files):
            raise PermissionDenied(gettext('This file has not been retrieved successfully.'))
        response = file_response(record)
        event(ticket, 'transfer.downloaded', file_id=str(record.pk), name=record.name, sha256=record.sha256)
        return response
