# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http.response import JsonResponse
from rest_framework import permissions
from rest_framework.request import Request

from common.exceptions import UserConfirmRequired
from audits.utils import create_operate_log
from audits.models import OperateLog

__all__ = ["PermissionsMixin", "RecordViewLogMixin", "UserConfirmRequiredExceptionMixin"]


class UserConfirmRequiredExceptionMixin:
    """
    异常处理
    """
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except UserConfirmRequired as e:
            return JsonResponse(e.detail, status=e.status_code)


class PermissionsMixin(UserPassesTestMixin):
    permission_classes = [permissions.IsAuthenticated]
    request: Request

    def get_permissions(self):
        return self.permission_classes

    def test_func(self):
        permission_classes = self.get_permissions()
        for permission_class in permission_classes:
            if not permission_class().has_permission(self.request, self):
                return False
        return True


class RecordViewLogMixin:
    ACTION = OperateLog.ACTION_VIEW

    @staticmethod
    def get_resource_display(request):
        query_params = dict(request.query_params)
        if query_params.get('format'):
            query_params.pop('format')
        spm_filter = query_params.pop('spm') if query_params.get('spm') else None
        if not query_params and not spm_filter:
            display_message = _('Export all')
        elif spm_filter:
            display_message = _('Export only selected items')
        else:
            query = ','.join(
                ['%s=%s' % (key, value) for key, value in query_params.items()]
            )
            display_message = _('Export filtered: %s') % query
        return display_message

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        resource = self.get_resource_display(request)
        create_operate_log(self.ACTION, self.model, resource)
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        create_operate_log(self.ACTION, self.model, self.get_object())
        return response
