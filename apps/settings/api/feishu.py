from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import GenericAPIView
from rest_framework.views import Response

from common.sdk.im.feishu import FeiShu
from settings.models import Setting
from .. import serializers


class FeiShuTestingAPI(GenericAPIView):
    category = 'FEISHU'
    serializer_class = serializers.FeiShuSettingSerializer
    rbac_perms = {
        'POST': 'settings.change_auth'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        app_id = serializer.validated_data[f'{self.category}_APP_ID']
        app_secret = serializer.validated_data.get(f'{self.category}_APP_SECRET')

        if not app_secret:
            secret = Setting.objects.filter(name=f'{self.category}_APP_SECRET').first()
            if secret:
                app_secret = secret.cleaned_value

        app_secret = app_secret or ''

        try:
            feishu = FeiShu(app_id=app_id, app_secret=app_secret)
            feishu.send_text(['test'], 'test')
            return Response(status=status.HTTP_200_OK, data={'msg': _('Test success')})
        except APIException as e:
            try:
                error = e.detail['errmsg']
            except:
                error = e.detail
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': error})


class LarkTestingAPI(FeiShuTestingAPI):
    category = 'LARK'
    serializer_class = serializers.LarkSettingSerializer
