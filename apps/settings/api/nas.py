# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView, Response

from common.utils import get_logger

logger = get_logger(__file__)

__all__ = ['NasTestingAPI']


class NasTestingAPI(APIView):
    success_message = _("NAS connection test successful, mount path is accessible")
    rbac_perms = {
        'POST': 'settings.change_terminal'
    }

    def post(self, request):
        config = {
            'nas_type': getattr(settings, 'NAS_TYPE', 'nfs'),
            'nas_host': getattr(settings, 'NAS_HOST', ''),
            'nas_port': getattr(settings, 'NAS_PORT', 0),
            'nas_share_name': getattr(settings, 'NAS_SHARE_NAME', ''),
            'nas_username': getattr(settings, 'NAS_USERNAME', ''),
            'nas_password': getattr(settings, 'NAS_PASSWORD', ''),
        }
        for field, key in (
            ('NAS_TYPE', 'nas_type'), ('NAS_HOST', 'nas_host'), ('NAS_PORT', 'nas_port'),
            ('NAS_SHARE_NAME', 'nas_share_name'), ('NAS_USERNAME', 'nas_username'),
            ('NAS_PASSWORD', 'nas_password'),
        ):
            if field in request.data:
                config[key] = request.data[field]

        from settings.tools.nas_mount import test_nas_connection
        ok, message = test_nas_connection(config)
        if not ok:
            return Response({"error": str(message)}, status=400)

        return Response({"msg": str(self.success_message)})
