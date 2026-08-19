# -*- coding: utf-8 -*-
#
import logging
import os

from django.conf import settings
from django.http import FileResponse
from django.utils.encoding import escape_uri_path
from django.utils.translation import gettext_lazy as _, gettext
from rest_framework.views import Response, APIView

from common.utils import get_logger

logger = get_logger(__file__)

__all__ = ['SyslogTestingAPI', 'SyslogDocDownloadAPI']


class SyslogTestingAPI(APIView):
    success_message = _("Test message sent, please check")
    rbac_perms = {
        'POST': 'settings.change_other'
    }

    def post(self, request):
        host = getattr(settings, 'SYSLOG_HOST', '')
        if not host:
            return Response(
                {"error": str(_("Syslog host is not configured"))},
                status=400
            )

        syslog_logger = logging.getLogger('syslog')
        syslog_handlers = [
            h for h in syslog_logger.handlers
            if h.__class__.__name__ == 'SysLogHandler'
        ]
        if not syslog_handlers:
            return Response(
                {"error": str(_("Syslog handler is not active, please save configuration first"))},
                status=400
            )

        try:
            message = _("Test syslog setting")
            syslog_logger.info(message)
        except Exception as e:
            logger.error("Failed to send test syslog message: %s", e)
            return Response({"error": str(e)}, status=400)

        return Response({"msg": str(self.success_message)})


class SyslogDocDownloadAPI(APIView):
    rbac_perms = {
        'GET': 'settings.change_other'
    }

    def get(self, request):
        doc_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
        doc_path = os.path.join(doc_dir, 'syslog_format_sample.docx')
        if not os.path.exists(doc_path):
            return Response(
                {"error": str(_("Syslog format document not found"))},
                status=404
            )

        filename = '{}.docx'.format(gettext('Syslog format document'))
        try:
            response = FileResponse(
                open(doc_path, 'rb'),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = "attachment; filename*=UTF-8''{}".format(
                escape_uri_path(filename)
            )
            return response
        except Exception as e:
            logger.error("Failed to download syslog format document: %s", e)
            return Response({"error": str(e)}, status=400)
