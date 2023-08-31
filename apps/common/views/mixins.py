# -*- coding: utf-8 -*-
#
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http.response import JsonResponse
from django.db.models import Model
from django.utils import translation
from rest_framework import permissions
from rest_framework.request import Request

from audits.const import ActivityChoices
from audits.handler import create_or_update_operate_log
from audits.models import ActivityLog
from common.exceptions import UserConfirmRequired
from orgs.utils import current_org

__all__ = [
    "PermissionsMixin",
    "RecordViewLogMixin",
    "UserConfirmRequiredExceptionMixin",
]


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
    model: Model

    def record_logs(self, ids, action, detail, model=None, **kwargs):
        with translation.override('en'):
            model = model or self.model
            resource_type = model._meta.verbose_name
            create_or_update_operate_log(
                action, resource_type, force=True, **kwargs
            )
            activities = [
                ActivityLog(
                    resource_id=resource_id, type=ActivityChoices.operate_log,
                    detail=detail, org_id=current_org.id,
                )
                for resource_id in ids
            ]
            ActivityLog.objects.bulk_create(activities)
