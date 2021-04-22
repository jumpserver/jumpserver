import requests

from rest_framework.views import Response
from rest_framework.generics import GenericAPIView

from common.permissions import IsSuperUser
from common.message.backends.dingtalk import URL

from .. import serializers


class DingTalkTestingAPI(GenericAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.DingTalkSettingSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        dingtalk_appkey = serializer.validated_data['DINGTALK_APPKEY']
        dingtalk_agentid = serializer.validated_data['DINGTALK_AGENTID']
        dingtalk_appsecret = serializer.validated_data['DINGTALK_APPSECRET']

        try:
            params = {'appkey': dingtalk_appkey, 'appsecret': dingtalk_appsecret}
            resp = requests.get(url=URL.GET_TOKEN, params=params)
            if resp.status_code != 200:
                return Response(status=400, data={'error': resp.json()})

            data = resp.json()
            errcode = data['errcode']
            if errcode != 0:
                return Response(status=400, data={'error': data['errmsg']})

            return Response(status=200)
        except Exception as e:
            return Response(status=400, data={'error': str(e)})
