# -*- coding: utf-8 -*-
#
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from common.utils import get_logger, get_object_or_none
from common.permissions import IsOrgAdmin
from ..models import LoginConfirmSetting
from ..serializers import LoginConfirmSettingSerializer
from .. import errors

__all__ = ['LoginConfirmSettingUpdateApi', 'LoginConfirmTicketStatusApi']
logger = get_logger(__name__)


class LoginConfirmSettingUpdateApi(UpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = LoginConfirmSettingSerializer

    def get_object(self):
        from users.models import User
        user_id = self.kwargs.get('user_id')
        user = get_object_or_404(User, pk=user_id)
        defaults = {'user': user}
        s, created = LoginConfirmSetting.objects.get_or_create(
            defaults, user=user,
        )
        return s


class LoginConfirmTicketStatusApi(APIView):
    permission_classes = ()

    def get_ticket(self):
        from tickets.models import LoginConfirmTicket
        ticket_id = self.request.session.get("auth_ticket_id")
        logger.debug('Login confirm ticket id: {}'.format(ticket_id))
        if not ticket_id:
            ticket = None
        else:
            ticket = get_object_or_none(LoginConfirmTicket, pk=ticket_id)
        return ticket

    def get(self, request, *args, **kwargs):
        ticket_id = self.request.session.get("auth_ticket_id")
        ticket = self.get_ticket()
        try:
            if not ticket:
                raise errors.LoginConfirmOtherError(ticket_id, _("not found"))
            if ticket.status == 'open':
                raise errors.LoginConfirmWaitError(ticket_id)
            elif ticket.action == ticket.ACTION_APPROVE:
                self.request.session["auth_confirm"] = "1"
                return Response({"msg": "ok"})
            elif ticket.action == ticket.ACTION_REJECT:
                raise errors.LoginConfirmOtherError(
                    ticket_id, ticket.get_action_display()
                )
            else:
                raise errors.LoginConfirmOtherError(
                    ticket_id, ticket.get_status_display()
                )
        except errors.AuthFailedError as e:
            return Response(e.as_data(), status=400)

    def delete(self, request, *args, **kwargs):
        ticket = self.get_ticket()
        if ticket:
            ticket.perform_status('closed', request.user)
        return Response('', status=200)
