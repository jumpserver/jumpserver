from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.decorators import action

from common.http import is_true
from common.permissions import IsValidUser
from common.const.http import GET, PATCH, POST
from common.drf.api import JmsGenericViewSet
from ..serializers import (
    SiteMessageDetailSerializer, SiteMessageIdsSerializer,
    SiteMessageSendSerializer,
)
from ..site_msg import SiteMessageUtil
from ..filters import SiteMsgFilter

__all__ = ('SiteMessageViewSet', )


class SiteMessageViewSet(ListModelMixin, RetrieveModelMixin, JmsGenericViewSet):
    permission_classes = (IsValidUser,)
    serializer_classes = {
        'default': SiteMessageDetailSerializer,
        'mark_as_read': SiteMessageIdsSerializer,
        'send': SiteMessageSendSerializer,
    }
    filterset_class = SiteMsgFilter

    def get_queryset(self):
        user = self.request.user
        has_read = self.request.query_params.get('has_read')

        if has_read is None:
            msgs = SiteMessageUtil.get_user_all_msgs(user.id)
        else:
            msgs = SiteMessageUtil.filter_user_msgs(user.id, has_read=is_true(has_read))
        return msgs

    @action(methods=[GET], detail=False, url_path='unread-total')
    def unread_total(self, request, **kwargs):
        user = request.user
        msgs = SiteMessageUtil.filter_user_msgs(user.id, has_read=False)
        return Response(data={'total': msgs.count()})

    @action(methods=[PATCH], detail=False, url_path='mark-as-read')
    def mark_as_read(self, request, **kwargs):
        user = request.user
        seri = self.get_serializer(data=request.data)
        seri.is_valid(raise_exception=True)
        ids = seri.validated_data['ids']
        SiteMessageUtil.mark_msgs_as_read(user.id, ids)
        return Response({'detail': 'ok'})

    @action(methods=[POST], detail=False)
    def send(self, request, **kwargs):
        seri = self.get_serializer(data=request.data)
        seri.is_valid(raise_exception=True)
        SiteMessageUtil.send_msg(**seri.validated_data, sender=request.user)
        return Response({'detail': 'ok'})
