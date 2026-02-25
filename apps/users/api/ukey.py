import base64

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.sdk.gm import piico
from common.sdk.gm.piico.exception import PiicoError
from common.utils import get_logger
from ..models import UKey
from ..serializers import UKeySerializer

logger = get_logger(__name__)


class UserUKeyViewSet(viewsets.ModelViewSet):
    queryset = UKey.objects.all()
    serializer_class = UKeySerializer
    search_fields = (
        "user__name",
        "u_key_serial",
    )
    filterset_fields = ("user",)
    permission_classes = (AllowAny,)

    @action(detail=False, methods=["get"], url_path="random")
    def get_ukey_random(self, *args, **kwargs):
        if not settings.PIICO_DEVICE_ENABLE:
            return Response({"msg": _("Piico device not enabled")}, status=400)

        device = piico.open_piico_device()
        try:
            random_bytes = device.generate_random(32)
            return Response({"msg": base64.b16encode(random_bytes)}, status=200)
        except PiicoError as e:
            return Response({"msg": _("Generate random failed: {}").format(e)}, status=400)
        except Exception:
            return Response({"msg": _("Device not initialized")}, status=400)
