from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.decorators import action

from common.permissions import IsValidUser
from common.const.http import GET
from common.drf.api import JmsGenericViewSet
from .models import SiteMessage
from .serializers import SiteMessageListSerializer, SiteMessageRetrieveSerializer
from . import message


class SiteMessageViewSet(ListModelMixin, RetrieveModelMixin, JmsGenericViewSet):
    permission_classes = (IsValidUser,)
    serializer_classes = {
        'retrieve': SiteMessageRetrieveSerializer,
        'unread': SiteMessageListSerializer,
        'list': SiteMessageListSerializer
    }

    def get_queryset(self):
        user = self.request.user
        msgs = message.get_user_all_msgs(user.id)
        return msgs

    @action(methods=[GET], detail=False)
    def unread(self, request, **kwargs):
        user = request.user
        msgs = message.get_user_unread_msgs(user.id)
        msgs = self.filter_queryset(msgs)
        return self.get_paginated_response_with_query_set(msgs)

    @action(methods=[GET], detail=False)
    def all(self, request, **kwargs):
        user = request.user
        msgs = message.get_user_all_msgs(user.id)
        return self.get_paginated_response_with_query_set(msgs)

    @action(methods=[GET], detail=True)
    def mark_as_read(self, request, pk, **kwargs):
        user = request.user
        message.mark_msg_as_read(user.id, pk)
        return Response({'detail': True})
