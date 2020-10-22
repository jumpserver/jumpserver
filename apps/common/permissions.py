# -*- coding: utf-8 -*-
#
import time
from copy import deepcopy

from rest_framework import exceptions
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings
from rest_framework import permissions

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


class SystemRBACPermission(permissions.DjangoModelPermissions):
    perms_map = {
        'list': ['view'],
        'retrieve': ['view'],
        'create': ['add'],
        'update': ['change'],
        'partial_update': ['change'],
        'destroy': ['delete'],
        'metadata': [],  # for OPTIONS method
    }

    @staticmethod
    def get_perm_code(perm_action, model_cls):
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        return f'%(app_label)s.{perm_action}_%(model_name)s' % kwargs

    def get_action_required_permissions(self, view, model_cls):
        """
        Given a model and an action, return the list of permission
        codes that the user is required to have.
        """
        extra_action_perms_map = getattr(view, 'extra_action_perms_map', {})
        perms_map = deepcopy(self.perms_map)
        perms_map.update(extra_action_perms_map)

        if view.action not in perms_map:
            raise exceptions.MethodNotAllowed(view.action)

        perms = []
        for perm_action in perms_map[view.action]:
            perms.append(self.get_perm_code(perm_action, model_cls))
        return perms

    def user_is_valid(self, request):
        if not request.user or \
                (not request.user.is_authenticated and self.authenticated_users_only):
            return False
        return True

    def has_permission(self, request, view):
        if view.action == 'metadata':
            return True
        if not self.user_is_valid(request):
            return False
        queryset = self._queryset(view)
        perms = self.get_action_required_permissions(view, queryset.model)
        return request.user.has_perms(perms)


