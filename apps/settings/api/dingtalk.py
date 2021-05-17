from rest_framework.views import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from settings.models import Setting
from common.permissions import IsSuperUser
from common.message.backends.dingtalk import DingTalk

from .. import serializers


class DingTalkTestingAPI(GenericAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.DingTalkSettingSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        dingtalk_appkey = serializer.validated_data['DINGTALK_APPKEY']
        dingtalk_agentid = serializer.validated_data['DINGTALK_AGENTID']
        dingtalk_appsecret = serializer.validated_data.get('DINGTALK_APPSECRET')

        if not dingtalk_appsecret:
            secret = Setting.objects.filter(name='DINGTALK_APPSECRET').first()
            if not secret:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': _('AppSecret is required')})
            dingtalk_appsecret = secret.cleaned_value

        try:
            dingtalk = DingTalk(appid=dingtalk_appkey, appsecret=dingtalk_appsecret, agentid=dingtalk_agentid)
            dingtalk.send_text(['test'], 'test')
            return Response(status=status.HTTP_200_OK, data={'msg': _('OK')})
        except APIException as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': e.detail})
