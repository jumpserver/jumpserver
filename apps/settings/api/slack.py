from rest_framework.views import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from settings.models import Setting
from common.sdk.im.slack import Slack

from .. import serializers


class SlackTestingAPI(GenericAPIView):
    serializer_class = serializers.SlackSettingSerializer
    rbac_perms = {
        'POST': 'settings.change_auth'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        bot_token = serializer.validated_data.get('SLACK_BOT_TOKEN')
        if not bot_token:
            secret = Setting.objects.filter(name='SLACK_BOT_TOKEN').first()
            if secret:
                bot_token = secret.cleaned_value

        bot_token = bot_token or ''

        try:
            slack = Slack(bot_token=bot_token)
            slack.is_valid()
            return Response(status=status.HTTP_200_OK, data={'msg': _('Test success')})
        except APIException as e:
            try:
                error = e.detail['errmsg']
            except:
                error = e.detail
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': error})
