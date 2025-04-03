# -*- coding: utf-8 -*-
#
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http.response import JsonResponse
from rest_framework import permissions
from rest_framework.request import Request

from common.exceptions import UserConfirmRequired


__all__ = [
    "PermissionsMixin",
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
