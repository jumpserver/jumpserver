from rest_framework.views import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from settings.models import Setting
from common.sdk.im.wecom import WeCom

from .. import serializers


class WeComTestingAPI(GenericAPIView):
    serializer_class = serializers.WeComSettingSerializer
    rbac_perms = {
        'POST': 'settings.change_auth'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        wecom_corpid = serializer.validated_data['WECOM_CORPID']
        wecom_agentid = serializer.validated_data['WECOM_AGENTID']
        wecom_corpsecret = serializer.validated_data.get('WECOM_SECRET')

        if not wecom_corpsecret:
            secret = Setting.objects.filter(name='WECOM_SECRET').first()
            if secret:
                wecom_corpsecret = secret.cleaned_value

        wecom_corpsecret = wecom_corpsecret or ''

        try:
            wecom = WeCom(corpid=wecom_corpid, corpsecret=wecom_corpsecret, agentid=wecom_agentid)
            wecom.send_text(['test'], 'test')
            return Response(status=status.HTTP_200_OK, data={'msg': _('Test success')})
        except APIException as e:
            try:
                error = e.detail['errmsg']
            except:
                error = e.detail
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': error})
