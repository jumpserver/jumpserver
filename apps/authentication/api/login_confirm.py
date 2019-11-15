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
from .. import errors, mixins

__all__ = ['LoginConfirmSettingUpdateApi', 'TicketStatusApi']
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


class TicketStatusApi(mixins.AuthMixin, APIView):
    permission_classes = ()

    def get_ticket(self):
        from tickets.models import Ticket
        ticket_id = self.request.session.get("auth_ticket_id")
        logger.debug('Login confirm ticket id: {}'.format(ticket_id))
        if not ticket_id:
            ticket = None
        else:
            ticket = get_object_or_none(Ticket, pk=ticket_id)
        return ticket

    def get(self, request, *args, **kwargs):
        try:
            self.check_user_login_confirm()
            return Response({"msg": "ok"})
        except errors.NeedMoreInfoError as e:
            return Response(e.as_data(), status=200)

    def delete(self, request, *args, **kwargs):
        ticket = self.get_ticket()
        if ticket:
            request.session.pop('auth_ticket_id', '')
            ticket.perform_status('closed', request.user)
        return Response('', status=200)
