import requests

from rest_framework.views import Response
from rest_framework.generics import GenericAPIView
from django.utils.translation import gettext_lazy as _

from common.permissions import IsSuperUser
from common.message.backends.wecom import URL

from .. import serializers


class WeComTestingAPI(GenericAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.WeComSettingSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        wecom_corpid = serializer.validated_data['WECOM_CORPID']
        wecom_agentid = serializer.validated_data['WECOM_AGENTID']
        wecom_corpsecret = serializer.validated_data['WECOM_SECRET']

        try:
            params = {'corpid': wecom_corpid, 'corpsecret': wecom_corpsecret}
            resp = requests.get(url=URL.GET_TOKEN, params=params)
            if resp.status_code != 200:
                return Response(status=400, data={'error': resp.json()})

            data = resp.json()
            errcode = data['errcode']
            if errcode != 0:
                return Response(status=400, data={'error': data['errmsg']})

            return Response(status=200, data={'msg': _('OK')})
        except Exception as e:
            return Response(status=400, data={'error': str(e)})
