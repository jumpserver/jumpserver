# -*- coding: utf-8 -*-
#
from django.utils import translation
from django.utils.translation import gettext_noop
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http.response import JsonResponse
from rest_framework import permissions
from rest_framework.request import Request

from common.exceptions import UserConfirmRequired
from common.utils import i18n_fmt
from orgs.utils import current_org
from audits.handler import create_or_update_operate_log
from audits.const import ActionChoices, ActivityChoices
from audits.models import ActivityLog

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
    ACTION = ActionChoices.view

    @staticmethod
    def _filter_params(params):
        new_params = {}
        need_pop_params = ('format', 'order')
        for key, value in params.items():
            if key in need_pop_params:
                continue
            if isinstance(value, list):
                value = list(filter(None, value))
            if value:
                new_params[key] = value
        return new_params

    def get_resource_display(self, request):
        query_params = dict(request.query_params)
        params = self._filter_params(query_params)

        spm_filter = params.pop("spm", None)

        if not params and not spm_filter:
            display_message = gettext_noop("Export all")
        elif spm_filter:
            display_message = gettext_noop("Export only selected items")
        else:
            query = ",".join(
                ["%s=%s" % (key, value) for key, value in params.items()]
            )
            display_message = i18n_fmt(gettext_noop("Export filtered: %s"), query)
        return display_message

    def record_logs(self, ids, **kwargs):
        resource_type = self.model._meta.verbose_name
        create_or_update_operate_log(
            self.ACTION, resource_type, force=True, **kwargs
        )
        detail = i18n_fmt(
            gettext_noop('User %s view/export secret'), self.request.user
        )
        activities = [
            ActivityLog(
                resource_id=getattr(resource_id, 'pk', resource_id),
                type=ActivityChoices.operate_log, detail=detail, org_id=current_org,
            )
            for resource_id in ids
        ]
        ActivityLog.objects.bulk_create(activities)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        with translation.override('en'):
            resource_display = self.get_resource_display(request)
            ids = [q.id for q in self.get_queryset()]
            self.record_logs(ids, resource_display=resource_display)
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        with translation.override('en'):
            resource = self.get_object()
            self.record_logs([resource.id], resource=resource)
        return response
