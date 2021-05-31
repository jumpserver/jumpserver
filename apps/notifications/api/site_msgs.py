from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.decorators import action

from common.permissions import IsValidUser
from common.const.http import GET, PATCH, POST
from common.drf.api import JmsGenericViewSet
from ..serializers import (
    SiteMessageListSerializer, SiteMessageRetrieveSerializer, SiteMessageIdsSerializer,
    SiteMessageSendSerializer,
)
from ..site_msg import SiteMessage

__all__ = ('SiteMessageViewSet', )


class SiteMessageViewSet(ListModelMixin, RetrieveModelMixin, JmsGenericViewSet):
    permission_classes = (IsValidUser,)
    serializer_classes = {
        'retrieve': SiteMessageRetrieveSerializer,
        'unread': SiteMessageListSerializer,
        'list': SiteMessageListSerializer,
        'mark_as_read': SiteMessageIdsSerializer,
        'send': SiteMessageSendSerializer,
    }

    def get_queryset(self):
        user = self.request.user
        msgs = SiteMessage.get_user_all_msgs(user.id)
        return msgs

    @action(methods=[GET], detail=False)
    def unread(self, request, **kwargs):
        user = request.user
        msgs = SiteMessage.get_user_unread_msgs(user.id)
        msgs = self.filter_queryset(msgs)
        return self.get_paginated_response_with_query_set(msgs)

    @action(methods=[PATCH], detail=False)
    def mark_as_read(self, request, **kwargs):
        user = request.user
        seri = self.get_serializer(data=request.data)
        seri.is_valid(raise_exception=True)
        ids = seri.validated_data['ids']
        SiteMessage.mark_msgs_as_read(user.id, ids)
        return Response({'detail': 'ok'})

    @action(methods=[POST], detail=False)
    def send(self, request, **kwargs):
        seri = self.get_serializer(data=request.data)
        seri.is_valid(raise_exception=True)
        SiteMessage.send_msg(**seri.validated_data, sender=request.user)
        return Response({'detail': 'ok'})
