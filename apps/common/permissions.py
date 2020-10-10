# -*- coding: utf-8 -*-
#
import time
from copy import deepcopy

from django.contrib.auth import get_permission_codename
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings

from rbac.models import Role
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


class IsSuperAuditor(IsValidUser):
    def has_permission(self, request, view):
        return super(IsSuperAuditor, self).has_permission(request, view) \
               and request.user.is_super_auditor


class IsOrgAuditor(IsValidUser):
    def has_permission(self, request, view):
        if not current_org:
            return False
        return super(IsOrgAuditor, self).has_permission(request, view) \
               and current_org.can_audit_by(request.user)


class IsOrgAdmin(IsValidUser):
    """Allows access only to superuser"""

    def has_permission(self, request, view):
        if not current_org:
            return False
        return super(IsOrgAdmin, self).has_permission(request, view) \
            and current_org.can_admin_by(request.user)


class IsOrgAdminOrAppUser(IsValidUser):
    """Allows access between superuser and app user"""

    def has_permission(self, request, view):
        if not current_org:
            return False
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


class WithBootstrapToken(permissions.BasePermission):
    def has_permission(self, request, view):
        authorization = request.META.get('HTTP_AUTHORIZATION', '')
        if not authorization:
            return False
        request_bootstrap_token = authorization.split()[-1]
        return settings.BOOTSTRAP_TOKEN == request_bootstrap_token


class PermissionsMixin(UserPassesTestMixin):
    permission_classes = []

    def get_permissions(self):
        return self.permission_classes

    def test_func(self):
        permission_classes = self.get_permissions()
        for permission_class in permission_classes:
            if not permission_class().has_permission(self.request, self):
                return False
        return True


class UserCanUpdatePassword:
    def has_permission(self, request, view):
        return request.user.can_update_password()


class UserCanUpdateSSHKey:
    def has_permission(self, request, view):
        return request.user.can_update_ssh_key()


class NeedMFAVerify(permissions.BasePermission):
    def has_permission(self, request, view):
        mfa_verify_time = request.session.get('MFA_VERIFY_TIME', 0)
        if time.time() - mfa_verify_time < settings.SECURITY_MFA_VERIFY_TTL:
            return True
        return False


class CanUpdateDeleteUser(permissions.BasePermission):

    @staticmethod
    def has_delete_object_permission(request, view, obj):
        if request.user.is_anonymous:
            return False
        if not request.user.can_admin_current_org:
            return False
        # 超级管理员 / 组织管理员
        if str(request.user.id) == str(obj.id):
            return False
        # 超级管理员
        if request.user.is_superuser:
            if obj.is_superuser and obj.username in ['admin']:
                return False
            return True
        # 组织管理员
        if obj.is_superuser:
            return False
        if obj.is_super_auditor:
            return False
        if obj.can_admin_current_org:
            return False
        return True

    @staticmethod
    def has_update_object_permission(request, view, obj):
        if request.user.is_anonymous:
            return False
        if not request.user.can_admin_current_org:
            return False
        # 超级管理员 / 组织管理员
        if str(request.user.id) == str(obj.id):
            return True
        # 超级管理员
        if request.user.is_superuser:
            return True
        # 组织管理员
        if obj.is_superuser:
            return False
        if obj.is_super_auditor:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_anonymous:
            return False
        if not request.user.can_admin_current_org:
            return False
        if request.method in ['DELETE']:
            return self.has_delete_object_permission(request, view, obj)
        if request.method in ['PUT', 'PATCH']:
            return self.has_update_object_permission(request, view, obj)
        return True


class IsObjectOwner(IsValidUser):
    def has_object_permission(self, request, view, obj):
        return (super().has_object_permission(request, view, obj) and
                request.user == getattr(obj, 'user', None))


class RBACPermission(IsValidUser):
    perms_map = {
        'list': 'view',
        'retrieve': 'view',
        'create': 'add',
        'update': 'change',
        'partial_update': 'change',
        'destroy': 'delete',
    }

    def has_permission(self, request, view):
        extra_action_perms_map = getattr(view, 'extra_action_perms_map', {})
        perms_map = deepcopy(self.perms_map)
        perms_map.update(extra_action_perms_map)
        action = perms_map.get(view.action)
        obj = None
        pk = view.kwargs.get('pk')
        if pk:
            obj = get_object_or_404(view.model, pk=pk)
        view_codename = get_permission_codename(action, view.model._meta)
        perm = '%s.%s' % (view.model._meta.app_label, view_codename)
        return super().has_permission(request, view) and \
            request.user.has_perm(perm, obj=obj)


class IsSystemAdminUser(IsValidUser):

    def has_permission(self, request, view):
        return super(IsSystemAdminUser, self).has_permission(request, view) and \
               Role.TypeChoices.system in request.user.rbac_role


class IsOrgAdminUser(IsValidUser):

    def has_permission(self, request, view):
        return super(IsOrgAdminUser, self).has_permission(request, view) and \
               Role.TypeChoices.org in request.user.rbac_role


class IsSystemOrOrgAdminUser(IsValidUser):

    def has_permission(self, request, view):
        return super(IsSystemOrOrgAdminUser, self).has_permission(request, view) and \
               (Role.TypeChoices.org in request.user.rbac_role or
                Role.TypeChoices.system in request.user.rbac_role)


class IsNamespaceUser(IsValidUser):

    def has_permission(self, request, view):
        return super(IsNamespaceUser, self).has_permission(request, view) and \
               Role.TypeChoices.namespace in request.user.rbac_role
