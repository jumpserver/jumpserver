from django.utils.translation import gettext_lazy as _
from requests.exceptions import RequestException
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from common.sdk.im.dingtalk import DingTalkRequests
from .. import serializers
from ..connection_testing import get_test_config, verify_im_credentials


class DingTalkTestingAPI(GenericAPIView):
    serializer_class = serializers.DingTalkSettingSerializer
    rbac_perms = {'POST': 'settings.change_auth'}

    def post(self, request):
        config = get_test_config(self.serializer_class, request.data, ('DINGTALK_APPSECRET',))
        try:
            verify_im_credentials(
                DingTalkRequests, appid=config['DINGTALK_APPKEY'],
                appsecret=config['DINGTALK_APPSECRET'], agentid=config['DINGTALK_AGENTID'],
            )
        except APIException as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                detail = detail.get('errmsg') or detail.get('msg') or detail
            return Response({'error': detail}, status=status.HTTP_400_BAD_REQUEST)
        except RequestException:
            return Response(
                {'error': _('Unable to connect to the service')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'msg': _('Test success')})
