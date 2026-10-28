from django.utils.translation import gettext_lazy as _
from requests.exceptions import RequestException
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from common.sdk.im.feishu import FeishuRequests
from common.sdk.im.lark import LarkRequests
from .. import serializers
from ..connection_testing import get_test_config, verify_im_credentials


class FeiShuTestingAPI(GenericAPIView):
    category = 'FEISHU'
    serializer_class = serializers.FeiShuSettingSerializer
    rbac_perms = {'POST': 'settings.change_auth'}

    def post(self, request):
        config = get_test_config(
            self.serializer_class, request.data, (f'{self.category}_APP_SECRET',)
        )
        try:
            verify_im_credentials(
                FeishuRequests if self.category == 'FEISHU' else LarkRequests,
                app_id=config[f'{self.category}_APP_ID'],
                app_secret=config[f'{self.category}_APP_SECRET'],
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
