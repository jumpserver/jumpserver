# -*- coding: utf-8 -*-
#
import os

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
        nas_enabled = getattr(settings, 'NAS_ENABLED', False)
        nas_type = getattr(settings, 'NAS_TYPE', 'nfs')
        nas_host = getattr(settings, 'NAS_HOST', '')
        nas_share_name = getattr(settings, 'NAS_SHARE_NAME', '')
        nas_mount_path = getattr(settings, 'NAS_MOUNT_PATH', '')
        nas_username = getattr(settings, 'NAS_USERNAME', '')
        nas_password = getattr(settings, 'NAS_PASSWORD', '')

        if not nas_enabled:
            return Response(
                {"error": str(_("NAS storage is not enabled"))},
                status=400
            )

        if not nas_host:
            return Response(
                {"error": str(_("NAS host is not configured"))},
                status=400
            )

        if not nas_mount_path:
            return Response(
                {"error": str(_("NAS mount path is not configured"))},
                status=400
            )

        # CIFS requires username
        if nas_type == 'cifs' and not nas_username:
            return Response(
                {"error": str(_("NAS username is required for CIFS"))},
                status=400
            )

        # Test if mount path exists and is writable
        if not os.path.exists(nas_mount_path):
            return Response(
                {"error": str(_("NAS mount path does not exist: {}")).format(nas_mount_path)},
                status=400
            )

        if not os.path.isdir(nas_mount_path):
            return Response(
                {"error": str(_("NAS mount path is not a directory: {}")).format(nas_mount_path)},
                status=400
            )

        # Test write permission by creating and removing a temp file
        try:
            test_file = os.path.join(nas_mount_path, '.jumpserver_nas_test')
            with open(test_file, 'w') as f:
                f.write('JumpServer NAS connectivity test')
            os.remove(test_file)
        except PermissionError:
            return Response(
                {"error": str(_("NAS mount path is not writable: {}")).format(nas_mount_path)},
                status=400
            )
        except OSError as e:
            return Response(
                {"error": str(_("NAS mount path I/O error: {}")).format(str(e))},
                status=400
            )

        return Response({"msg": str(self.success_message)})
