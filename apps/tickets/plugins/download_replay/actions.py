from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied

from common.drf.throttling import FileTransferThrottle
from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.plugins.actions import TicketAction


class DownloadReplay(TicketAction):
    method = 'GET'
    throttle_classes = (FileTransferThrottle,)

    def execute(self, ticket, request):
        from terminal.api.session.session import SessionViewSet
        from terminal.models import Session
        from tickets.models import Ticket, WorkflowEvent
        from tickets.plugins import get_ticket_plugin
        from tickets.workflow.approvers import user_snapshot

        plugin = get_ticket_plugin('download_replay')

        def authorize():
            # Re-read the approval before sending: packaging can take time.
            with tmp_to_root_org():
                current = get_object_or_404(Ticket, pk=ticket.pk, org_id=ticket.org_id)
            actions, status = plugin.get_replay_access(current, request.user)
            if not actions:
                raise PermissionDenied({'detail': _('No active approval for this session recording.'),
                                        'state': status['state']})
            return current, actions[0]

        current_ticket, access = authorize()

        def before_send():
            current_ticket, current_access = authorize()
            if current_access['session_id'] != access['session_id'] or current_ticket.org_id != ticket.org_id:
                raise PermissionDenied(_('The approved session recording changed.'))
            WorkflowEvent.objects.create(
                instance=current_ticket.workflow_instance, type='replay.downloaded', actor=request.user,
                actor_snapshot=user_snapshot(request.user),
                data={'session_id': access['session_id'], 'expires_at': current_access['expires_at']},
            )

        with tmp_to_org(ticket.org_id):
            session = get_object_or_404(Session, pk=access['session_id'], org_id=ticket.org_id, has_replay=True)
            try:
                return SessionViewSet.build_replay_download_response(session, request, before_send=before_send)
            except (OSError, ValueError) as exc:
                raise NotFound(_('The requested session recording is no longer available.')) from exc
