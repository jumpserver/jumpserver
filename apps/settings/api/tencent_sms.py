from collections import OrderedDict

from rest_framework.views import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from common.sdk.sms.tencent import TencentSMS
from settings.models import Setting
from common.exceptions import JMSException

from .. import serializers


class TencentSMSTestingAPI(GenericAPIView):
    serializer_class = serializers.TencentSMSSettingSerializer
    rbac_perms = {
        'POST': 'settings.change_sms'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        tencent_secret_id = serializer.validated_data['TENCENT_SECRET_ID']
        tencent_secret_key = serializer.validated_data.get('TENCENT_SECRET_KEY')
        tencent_verify_sign_name = serializer.validated_data['TENCENT_VERIFY_SIGN_NAME']
        tencent_verify_template_code = serializer.validated_data['TENCENT_VERIFY_TEMPLATE_CODE']
        tencent_sdkappid = serializer.validated_data.get('TENCENT_SDKAPPID')

        test_phone = serializer.validated_data.get('SMS_TEST_PHONE')

        if not test_phone:
            raise JMSException(code='test_phone_required', detail=_('test_phone is required'))

        if not tencent_secret_key:
            secret = Setting.objects.filter(name='TENCENT_SECRET_KEY').first()
            if secret:
                tencent_secret_key = secret.cleaned_value

        tencent_secret_key = tencent_secret_key or ''

        try:
            client = TencentSMS(
                secret_id=tencent_secret_id,
                secret_key=tencent_secret_key,
                sdkappid=tencent_sdkappid
            )

            client.send_sms(
                phone_numbers=[test_phone],
                sign_name=tencent_verify_sign_name,
                template_code=tencent_verify_template_code,
                template_param=OrderedDict(code='666666')
            )
            return Response(status=status.HTTP_200_OK, data={'msg': _('Test success')})
        except APIException as e:
            try:
                error = e.detail['errmsg']
            except:
                error = e.detail
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': error})
