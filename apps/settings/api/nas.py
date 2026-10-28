# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView, Response

from common.utils import get_logger
from ..serializers import NasTestSerializer
from ..connection_testing import get_test_config

logger = get_logger(__file__)

__all__ = ['NasTestingAPI']


class NasTestingAPI(APIView):
    success_message = _("NAS connection test successful, mount path is accessible")
    rbac_perms = {
        'POST': 'settings.change_terminal'
    }

    def post(self, request):
        data = get_test_config(NasTestSerializer, request.data)
        config = {name.lower(): value for name, value in data.items()}

        from settings.tools.nas_mount import test_nas_connection
        ok, message = test_nas_connection(config)
        if not ok:
            return Response({"error": str(message)}, status=400)

        return Response({"msg": str(self.success_message)})
