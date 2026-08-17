# -*- coding: utf-8 -*-
#
import os

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView, Response

from common.utils import get_logger
from ..const import NAS_MOUNT_PATH

logger = get_logger(__file__)

__all__ = ['NasTestingAPI', 'NasArchiveAPI']


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
        nas_mount_path = NAS_MOUNT_PATH
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

        if not os.path.ismount(nas_mount_path):
            return Response(
                {"error": str(_("NAS mount path is not mounted: {}")).format(nas_mount_path)},
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


class NasArchiveAPI(APIView):
    rbac_perms = {
        'POST': 'settings.change_terminal'
    }

    def post(self, request):
        from datetime import datetime

        start_date_str = request.data.get('start_date', '')
        end_date_str = request.data.get('end_date', '')

        if not start_date_str and not end_date_str:
            return Response(
                {"error": _("At least one of start date and end date is required")},
                status=400
            )

        nas_enabled = getattr(settings, 'NAS_ENABLED', False)
        if not nas_enabled:
            return Response(
                {"error": _("NAS storage is not enabled")},
                status=400
            )

        if not os.path.ismount(nas_mount_path):
            return Response(
                {"error": _("NAS mount path is not mounted: {}").format(nas_mount_path)},
                status=400
            )

        def parse_date(date_str):
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return None

        start_date = parse_date(start_date_str) if start_date_str else None
        if start_date_str and start_date is None:
            return Response(
                {"error": _("Invalid start date format, please use YYYY-MM-DD")},
                status=400
            )

        end_date = parse_date(end_date_str) if end_date_str else None
        if end_date_str and end_date is None:
            return Response(
                {"error": _("Invalid end date format, please use YYYY-MM-DD")},
                status=400
            )

        if start_date and end_date and start_date > end_date:
            return Response(
                {"error": _("Start date cannot be later than end date")},
                status=400
            )

        from audits.tasks import nas_archive_session_replays
        task = nas_archive_session_replays.delay(
            start_date_str, end_date_str
        )

        logger.info(
            'NAS archive task enqueued: %s for range %s ~ %s',
            task.id, start_date_str or '-', end_date_str or '-'
        )

        return Response({
            "msg": _("Archive task started"),
            "task_id": task.id,
            "start_date": start_date_str or None,
            "end_date": end_date_str or None
        })
