# -*- coding: utf-8 -*-
#
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from common.utils import get_logger
from .. import errors, mixins
from django.contrib.auth import logout as auth_logout


__all__ = ['TicketStatusApi']
logger = get_logger(__name__)


class TicketStatusApi(mixins.AuthMixin, APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        try:
            self.check_user_login_confirm()
            self.request.session['auth_third_party_done'] = 1
            return Response({"msg": "ok"})
        except errors.LoginConfirmOtherError as e:
            self.send_auth_signal(success=False, user=request.user, username=request.user.name, reason=e.as_data().get('msg'))
            auth_logout(request)
            return Response(e.as_data(), status=200)
        except errors.NeedMoreInfoError as e:
            return Response(e.as_data(), status=200)

    def delete(self, request, *args, **kwargs):
        ticket = self.get_ticket()
        if ticket:
            request.session.pop('auth_ticket_id', '')
            ticket.close()
        return Response('', status=200)
