# -*- coding: utf-8 -*-
#
import time

from rest_framework import permissions
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.http.response import HttpResponseForbidden
from django.conf import settings

from orgs.utils import current_org


class IsValidUser(permissions.IsAuthenticated, permissions.BasePermission):
    """Allows access to valid user, is active and not expired"""

    def has_permission(self, request, view):
        return super(IsValidUser, self).has_permission(request, view) \
            and request.user.is_valid


class IsAppUser(IsValidUser):
    """Allows access only to app user """

    def has_permission(self, request, view):
        return super(IsAppUser, self).has_permission(request, view) \
            and request.user.is_app


class IsSuperUser(IsValidUser):
    def has_permission(self, request, view):
        return super(IsSuperUser, self).has_permission(request, view) \
               and request.user.is_superuser


class IsSuperUserOrAppUser(IsSuperUser):
    def has_permission(self, request, view):
        return super(IsSuperUserOrAppUser, self).has_permission(request, view) \
            or request.user.is_app


class IsOrgAdmin(IsValidUser):
    """Allows access only to superuser"""

    def has_permission(self, request, view):
        return super(IsOrgAdmin, self).has_permission(request, view) \
            and current_org.can_admin_by(request.user)


class IsOrgAdminOrAppUser(IsValidUser):
    """Allows access between superuser and app user"""

    def has_permission(self, request, view):
        return super(IsOrgAdminOrAppUser, self).has_permission(request, view) \
            and (current_org.can_admin_by(request.user) or request.user.is_app)


class IsOrgAdminOrAppUserOrUserReadonly(IsOrgAdminOrAppUser):
    def has_permission(self, request, view):
        if IsValidUser.has_permission(self, request, view) \
                and request.method in permissions.SAFE_METHODS:
            return True
        else:
            return IsOrgAdminOrAppUser.has_permission(self, request, view)


class IsCurrentUserOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user


class LoginRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_authenticated:
            return True
        else:
            return False


class AdminUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        elif not current_org.can_admin_by(self.request.user):
            self.raise_exception = True
            return False
        return True

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if not current_org:
            return redirect('orgs:switch-a-org')

        if not current_org.can_admin_by(request.user):
            if request.user.is_org_admin:
                return redirect('orgs:switch-a-org')
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)


class SuperUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return True


class WithBootstrapToken(permissions.BasePermission):
    def has_permission(self, request, view):
        authorization = request.META.get('HTTP_AUTHORIZATION', '')
        if not authorization:
            return False
        request_bootstrap_token = authorization.split()[-1]
        return settings.BOOTSTRAP_TOKEN == request_bootstrap_token
