# -*- coding: utf-8 -*-
#
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from common.utils import get_logger, get_object_or_none
from common.permissions import IsOrgAdmin
from ..models import LoginConfirmSetting
from ..serializers import LoginConfirmSettingSerializer
from .. import errors

__all__ = ['LoginConfirmSettingUpdateApi', 'UserTicketAcceptAuthApi']
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


class UserTicketAcceptAuthApi(APIView):
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        from tickets.models import LoginConfirmTicket
        ticket_id = self.request.session.get("auth_ticket_id")
        logger.debug('Login confirm ticket id: {}'.format(ticket_id))
        if not ticket_id:
            ticket = None
        else:
            ticket = get_object_or_none(LoginConfirmTicket, pk=ticket_id)
        try:
            if not ticket:
                raise errors.LoginConfirmTicketNotFound(ticket_id)
            if ticket.action == LoginConfirmTicket.ACTION_APPROVE:
                self.request.session["auth_confirm"] = "1"
                return Response({"msg": "ok"})
            elif ticket.action == LoginConfirmTicket.ACTION_REJECT:
                raise errors.LoginConfirmRejectedError(ticket_id)
            else:
                raise errors.LoginConfirmWaitError(ticket_id)
        except errors.AuthFailedError as e:
            data = e.as_data()
            return Response(data, status=400)


class UserTicketCancelAuthApi(APIView):
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        from tickets.models import LoginConfirmTicket
        ticket_id = self.request.session.get("auth_ticket_id")
        logger.debug('Login confirm ticket id: {}'.format(ticket_id))
        if not ticket_id:
            ticket = None
        else:
            ticket = get_object_or_none(LoginConfirmTicket, pk=ticket_id)
        if not ticket:
            ticket.status = "close"
