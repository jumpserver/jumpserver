# -*- coding: utf-8 -*-
#
import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.views import Response, APIView

from common.utils import get_logger

logger = get_logger(__file__)

__all__ = ['SyslogTestingAPI']


class SyslogTestingAPI(APIView):
    success_message = _("Test syslog message sent to {}, please check")
    rbac_perms = {
        'POST': 'settings.change_other'
    }

    def post(self, request):
        host = getattr(settings, 'SYSLOG_HOST', '')
        port = getattr(settings, 'SYSLOG_PORT', 514)
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

        addr = '{}:{}'.format(host, port)
        return Response({"msg": str(self.success_message.format(addr))})
