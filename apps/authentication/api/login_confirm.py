# -*- coding: utf-8 -*-
#
from django.contrib.auth import logout as auth_logout
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import get_logger
from .. import errors, mixins

__all__ = ['TicketStatusApi']
logger = get_logger(__name__)


class TicketStatusApi(mixins.AuthMixin, APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
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
            request.session.pop('auth_ticket_id', '')
            ticket.close()
        return Response('', status=200)
