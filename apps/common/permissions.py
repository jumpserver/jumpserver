# -*- coding: utf-8 -*-
#

from rest_framework import permissions
from django.contrib.auth.mixins import UserPassesTestMixin

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
    """Allows access only to superuser"""

    def has_permission(self, request, view):
        return super(IsSuperUser, self).has_permission(request, view) \
            and request.user.is_superuser


class IsSuperUserOrAppUser(IsValidUser):
    """Allows access between superuser and app user"""

    def has_permission(self, request, view):
        return super(IsSuperUserOrAppUser, self).has_permission(request, view) \
            and (request.user.is_superuser or request.user.is_app)


class IsSuperUserOrAppUserOrUserReadonly(IsSuperUserOrAppUser):
    def has_permission(self, request, view):
        if IsValidUser.has_permission(self, request, view) \
                and request.method in permissions.SAFE_METHODS:
            return True
        else:
            return IsSuperUserOrAppUser.has_permission(self, request, view)


class IsCurrentUserOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user


class AdminUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        elif not self.request.user:
            self.raise_exception = True
            return False
        return True
