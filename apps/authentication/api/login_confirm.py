# -*- coding: utf-8 -*-
#
from django.contrib.auth import logout as auth_logout
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import get_logger
from orgs.utils import tmp_to_org
from tickets.workflow.errors import WorkflowConflict
from .. import errors, mixins

__all__ = ['TicketStatusApi']

logger = get_logger(__name__)


class TicketStatusApi(mixins.AuthMixin, APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        # A poll can arrive after the login guard has cleared the review markers.
        if (request.user.is_authenticated and not request.session.get('auth_ticket_id')
                and not request.session.get('auth_confirm_required')):
            return Response({"msg": "ok"})
        try:
            self.check_user_login_confirm()
            self.request.session['auth_third_party_done'] = 1
            self.request.session.pop('auth_third_party_required', '')
            return Response({"msg": "ok"})
        except errors.LoginConfirmOtherError as e:
            reason = e.msg
            username = e.username
            self.send_auth_signal(success=False, username=username, reason=reason)
            auth_ticket_id = request.session.pop('auth_ticket_id', '')
            # 若为三方登录，此时应退出登录
            auth_logout(request)
            request.session['auth_ticket_id'] = auth_ticket_id
            return Response(e.as_data(), status=200)
        except errors.NeedMoreInfoError as e:
            return Response(e.as_data(), status=200)

    def delete(self, request, *args, **kwargs):
        ticket = self.get_ticket()
        if ticket:
            with tmp_to_org(ticket.org_id):
                try:
                    ticket.close()
                except WorkflowConflict:
                    # A concurrent approval or cancellation may have finished it.
                    ticket.refresh_from_db()
                    if ticket.is_status(ticket.Status.open):
                        raise
        request.session.pop('auth_ticket_id', '')
        return Response('', status=200)
