from rest_framework.request import Request
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.decorators import action

from common.permissions import IsValidUser
from common.const.http import GET
from common.drf.api import JmsGenericViewSet
from .models import SiteMessage
from .serializers import SiteMessageListSerializer, SiteMessageRetrieveSerializer
from . import message


class SiteMessageViewSet(JmsGenericViewSet):
    permission_classes = (IsValidUser,)
    queryset = SiteMessage.objects.all()
    serializer_classes = {
        'retrieve': SiteMessageRetrieveSerializer,
        'unread': SiteMessageListSerializer,
        'all': SiteMessageListSerializer
    }

    @action(methods=[GET], detail=False)
    def unread(self, request, **kwargs):
        user = request.user
        msgs = message.get_user_unread_msgs(user.id)
        return self.get_paginated_response_with_query_set(msgs)

    @action(methods=[GET], detail=False)
    def all(self, request, **kwargs):
        user = request.user
        msgs = message.get_user_all_msgs(user.id)
        return self.get_paginated_response_with_query_set(msgs)

    @action(methods=[GET], detail=True)
    def read(self, request, pk, **kwargs):
        user = request.user
        message.get_user_all_msgs(user.id)
