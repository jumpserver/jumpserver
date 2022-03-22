from rest_framework.views import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from django.conf import settings
from common.sdk.im.dingtalk import DingTalk
from .. import serializers


class DingTalkTestingAPI(GenericAPIView):
    serializer_class = serializers.DingTalkSettingSerializer
    rbac_perms = {
        'POST': 'settings.change_auth'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        app_key = serializer.validated_data['DINGTALK_APPKEY']
        agent_id = serializer.validated_data['DINGTALK_AGENTID']
        app_secret = serializer.validated_data.get('DINGTALK_APPSECRET') \
                     or settings.DINGTALK_APPSECRET \
                     or ''

        try:
            dingtalk = DingTalk(appid=app_key, appsecret=app_secret, agentid=agent_id)
            dingtalk.send_text(['test'], 'test')
            return Response(status=status.HTTP_200_OK, data={'msg': _('Test success')})
        except APIException as e:
            if 'errmsg' in e.detail:
                error = e.detail['errmsg']
            else:
                error = e.detail
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': error})
