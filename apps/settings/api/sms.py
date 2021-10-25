from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from common.permissions import IsSuperUser
from common.sdk.sms import BACKENDS
from settings.serializers.sms import SMSBackendSerializer


class SMSBackendAPI(ListAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = SMSBackendSerializer

    def list(self, request, *args, **kwargs):
        data = [
            {
                'name': b,
                'label': b.label
            }
            for b in BACKENDS
        ]

        return Response(data)
