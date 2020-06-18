# -*- coding: utf-8 -*-
#
import time
from django.utils import timezone
from django.shortcuts import HttpResponse
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.fields import DateTimeField
from rest_framework.response import Response
from django.template import loader


from orgs.utils import current_org
from common.permissions import IsOrgAdminOrAppUser, IsOrgAuditor
from common.utils import get_logger
from ..backends import (
    get_command_storage, get_multi_command_storage,
    SessionCommandSerializer,
)

logger = get_logger(__name__)
__all__ = ['CommandViewSet', 'CommandExportApi']


class CommandQueryMixin:
    command_store = get_command_storage()
    permission_classes = [IsOrgAdminOrAppUser | IsOrgAuditor]
    filter_fields = [
        "asset", "system_user", "user", "session", "risk_level",
        "input"
    ]
    default_days_ago = 5

    @staticmethod
    def get_org_id():
        if current_org.is_default():
            org_id = ''
        else:
            org_id = current_org.id
        return org_id

    def get_query_risk_level(self):
        risk_level = self.request.query_params.get('risk_level')
        if risk_level is None:
            return None
        if risk_level.isdigit():
            return int(risk_level)
        return None

    def get_queryset(self):
        # 解决访问 /docs/ 问题
        if hasattr(self, 'swagger_fake_view'):
            return self.command_store.model.objects.none()
        date_from, date_to = self.get_date_range()
        q = self.request.query_params
        multi_command_storage = get_multi_command_storage()
        queryset = multi_command_storage.filter(
            date_from=date_from, date_to=date_to, input=q.get("input"),
            user=q.get("user"), asset=q.get("asset"),
            system_user=q.get("system_user"),
            risk_level=self.get_query_risk_level(), org_id=self.get_org_id(),
        )
        return queryset

    def filter_queryset(self, queryset):
        return queryset

    def get_filter_fields(self, request):
        fields = self.filter_fields
        fields.extend(["date_from", "date_to"])
        return fields

    def get_date_range(self):
        now = timezone.now()
        days_ago = now - timezone.timedelta(days=self.default_days_ago)
        date_from_st = days_ago.timestamp()
        date_to_st = now.timestamp()

        query_params = self.request.query_params
        date_from_q = query_params.get("date_from")
        date_to_q = query_params.get("date_to")

        dt_parser = DateTimeField().to_internal_value

        if date_from_q:
            date_from_st = dt_parser(date_from_q).timestamp()

        if date_to_q:
            date_to_st = dt_parser(date_to_q).timestamp()
        return date_from_st, date_to_st


class CommandViewSet(CommandQueryMixin, viewsets.ModelViewSet):
    """接受app发送来的command log, 格式如下
    {
        "user": "admin",
        "asset": "localhost",
        "system_user": "web",
        "session": "xxxxxx",
        "input": "whoami",
        "output": "d2hvbWFp",  # base64.b64encode(s)
        "timestamp": 1485238673.0
    }

    """
    command_store = get_command_storage()
    serializer_class = SessionCommandSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, many=True)
        if serializer.is_valid():
            ok = self.command_store.bulk_save(serializer.validated_data)
            if ok:
                return Response("ok", status=201)
            else:
                return Response("Save error", status=500)
        else:
            msg = "Command not valid: {}".format(serializer.errors)
            logger.error(msg)
            return Response({"msg": msg}, status=401)


class CommandExportApi(CommandQueryMixin, generics.ListAPIView):
    serializer_class = SessionCommandSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        template = 'terminal/command_report.html'
        context = {
            'queryset': queryset,
            'total_count': len(queryset),
            'now': time.time(),
        }
        content = loader.render_to_string(template, context, request)
        content_type = 'application/octet-stream'
        response = HttpResponse(content, content_type)
        filename = 'command-report-{}.html'.format(int(time.time()))
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response
