# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404
from rest_framework.request import Request

from common.http import is_true
from common.mixins.api import RoleAdminMixin, RoleUserMixin
from perms.utils.user_permission import UserGrantedTreeRefreshController
from rbac.permissions import RBACPermission
from users.models import User


class RebuildTreeMixin:
    user: User

    def get(self, request: Request, *args, **kwargs):
        force = is_true(request.query_params.get('rebuild_tree'))
        controller = UserGrantedTreeRefreshController(self.user)
        controller.refresh_if_need(force)
        return super().get(request, *args, **kwargs)


class AssetRoleAdminMixin(RebuildTreeMixin, RoleAdminMixin):
    rbac_perms = (
        ('list', 'perms.view_userassets'),
        ('retrieve', 'perms.view_userassets'),
        ('get_tree', 'perms.view_userassets'),
        ('GET', 'perms.view_userassets'),
    )


class AssetRoleUserMixin(RebuildTreeMixin, RoleUserMixin):
    rbac_perms = (
        ('list', 'perms.view_myassets'),
        ('retrieve', 'perms.view_myassets'),
        ('get_tree', 'perms.view_myassets'),
        ('GET', 'perms.view_myassets'),
    )


class SelfOrPKUserMixin:
    kwargs: dict
    request: Request
    permission_classes = (RBACPermission,)

    @property
    def self_rbac_perms(self):
        return (
            ('list', 'perms.view_myassets'),
            ('retrieve', 'perms.view_myassets'),
            ('get_tree', 'perms.view_myassets'),
            ('GET', 'perms.view_myassets'),
        )

    @property
    def admin_rbac_perms(self):
        return (
            ('list', 'perms.view_userassets'),
            ('retrieve', 'perms.view_userassets'),
            ('get_tree', 'perms.view_userassets'),
            ('GET', 'perms.view_userassets'),
        )

    def get_rbac_perms(self):
        if self.request_user_is_self():
            return self.self_rbac_perms
        else:
            return self.admin_rbac_perms

    def request_user_is_self(self):
        print("user is: ", self.kwargs)
        return self.kwargs.get('user') in ['my', 'self']

    @property
    def user(self):
        if self.request_user_is_self():
            return self.request.user
        else:
            return get_object_or_404(User, pk=self.kwargs.get('user'))
