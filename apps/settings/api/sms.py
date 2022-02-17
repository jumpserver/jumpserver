from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from common.sdk.sms import BACKENDS
from settings.serializers.sms import SMSBackendSerializer


class SMSBackendAPI(ListAPIView):
    serializer_class = SMSBackendSerializer
    rbac_perms = {
        'list': 'settings.view_setting'
    }

    def list(self, request, *args, **kwargs):
        data = [
            {
                'name': b,
                'label': b.label
            }
            for b in BACKENDS.choices
        ]

        return Response(data)
