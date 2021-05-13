# -*- coding: utf-8 -*-
#
import time
from rest_framework import permissions
from django.conf import settings
from common.exceptions import MFAVerifyRequired

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


class UserCanAnyPermCurrentOrg(permissions.BasePermission):
    def has_permission(self, request, view):
        return current_org.can_any_by(request.user)


class UserCanUpdatePassword(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.can_update_password()


class UserCanUpdateSSHKey(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.can_update_ssh_key()


class NeedMFAVerify(permissions.BasePermission):
    def has_permission(self, request, view):
        mfa_verify_time = request.session.get('MFA_VERIFY_TIME', 0)
        if time.time() - mfa_verify_time < settings.SECURITY_MFA_VERIFY_TTL:
            return True
        raise MFAVerifyRequired()


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


class HasQueryParamsUserAndIsCurrentOrgMember(permissions.BasePermission):
    def has_permission(self, request, view):
        query_user_id = request.query_params.get('user')
        if not query_user_id:
            return False
        query_user = current_org.get_members().filter(id=query_user_id).first()
        return bool(query_user)
