from rest_framework.views import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from common.sdk.sms.alibaba import AlibabaSMS
from settings.models import Setting
from common.exceptions import JMSException

from .. import serializers


class AlibabaSMSTestingAPI(GenericAPIView):
    serializer_class = serializers.AlibabaSMSSettingSerializer
    rbac_perms = {
        'POST': 'settings.change_sms'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        alibaba_access_key_id = serializer.validated_data['ALIBABA_ACCESS_KEY_ID']
        alibaba_access_key_secret = serializer.validated_data.get('ALIBABA_ACCESS_KEY_SECRET')
        alibaba_verify_sign_name = serializer.validated_data['ALIBABA_VERIFY_SIGN_NAME']
        alibaba_verify_template_code = serializer.validated_data['ALIBABA_VERIFY_TEMPLATE_CODE']
        test_phone = serializer.validated_data.get('SMS_TEST_PHONE')

        if not test_phone:
            raise JMSException(code='test_phone_required', detail=_('test_phone is required'))

        if not alibaba_access_key_secret:
            secret = Setting.objects.filter(name='ALIBABA_ACCESS_KEY_SECRET').first()
            if secret:
                alibaba_access_key_secret = secret.cleaned_value

        alibaba_access_key_secret = alibaba_access_key_secret or ''

        try:
            client = AlibabaSMS(
                access_key_id=alibaba_access_key_id,
                access_key_secret=alibaba_access_key_secret
            )

            client.send_sms(
                phone_numbers=[test_phone],
                sign_name=alibaba_verify_sign_name,
                template_code=alibaba_verify_template_code,
                template_param={'code': 'test'}
            )
            return Response(status=status.HTTP_200_OK, data={'msg': _('Test success')})
        except APIException as e:
            try:
                error = e.detail['errmsg']
            except:
                error = e.detail
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': error})
