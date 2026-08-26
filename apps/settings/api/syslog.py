# -*- coding: utf-8 -*-
#
import logging
import os
from django.http import FileResponse
from django.utils.encoding import escape_uri_path
from django.utils.translation import gettext_lazy as _, gettext
from rest_framework.views import Response, APIView

from common.utils import get_logger
from .. import serializers

logger = get_logger(__file__)

__all__ = ['SyslogTestingAPI', 'SyslogDocDownloadAPI']


class SyslogTestingAPI(APIView):
    serializer_class = serializers.SyslogTestSerializer
    rbac_perms = {
        'POST': 'settings.change_other'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        from jumpserver.settings.logging import SyslogConfig, create_syslog_handler

        config = SyslogConfig.from_test_data(serializer.validated_data)
        handler = None
        try:
            handler = create_syslog_handler(config)
            record = logging.LogRecord(
                'syslog', logging.INFO, __file__, 0,
                'syslog_test - {"test": "message"}', (), None,
            )
            handler.emit(record)
        except Exception as e:
            logger.error("Failed to test syslog delivery: %s", e)
            return Response({"error": str(e)}, status=400)
        finally:
            if handler is not None:
                handler.close()

        return Response({"msg": _('Test success')})


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
