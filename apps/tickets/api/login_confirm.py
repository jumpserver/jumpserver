# -*- coding: utf-8 -*-
#
from rest_framework_bulk import BulkModelViewSet

from common.permissions import IsValidUser
from common.mixins import CommonApiMixin
from .. import serializers, mixins
from ..models import LoginConfirmTicket


class LoginConfirmTicketViewSet(CommonApiMixin, mixins.TicketMixin, BulkModelViewSet):
    serializer_class = serializers.LoginConfirmTicketSerializer
    permission_classes = (IsValidUser,)
    queryset = LoginConfirmTicket.objects.all()
    filter_fields = ['status', 'title', 'action', 'ip']
    search_fields = ['user_display', 'title', 'ip', 'city']
