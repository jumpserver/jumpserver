# -*- coding: utf-8 -*-
#
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.request import Request

from common.utils import lazyproperty

__all__ = ['AllowBulkDestroyMixin', 'RoleAdminMixin', 'RoleUserMixin']


class AllowBulkDestroyMixin:
    def allow_bulk_destroy(self, qs, filtered):
        """
        我们规定，批量删除的情况必须用 `id` 指定要删除的数据。
        """
        where = filtered.query.where

        def has_id_condition(node):
            # 检查是否有 `id` 或 `ptr_id` 的条件
            if isinstance(node, Q):
                return any(
                    lookup in str(node)
                    for lookup in ['id', 'ptr_id']
                )
            if hasattr(node, 'lhs') and hasattr(node, 'rhs'):
                return any(
                    lookup in str(node.lhs)
                    for lookup in ['id', 'ptr_id']
                )
            return False

        def check_conditions(where):
            if hasattr(where, 'children'):
                for child in where.children:
                    if has_id_condition(child):
                        return True
                    if hasattr(child, 'children') and check_conditions(child):
                        return True
            return False

        can = check_conditions(where)
        return can


class RoleAdminMixin:
    kwargs: dict
    user_id_url_kwarg = 'pk'

    @lazyproperty
    def user(self):
        user_id = self.kwargs.get(self.user_id_url_kwarg)
        if hasattr(self, 'swagger_fake_view') and not user_id:
            return self.request.user  # NOQA
        user_model = get_user_model()
        return user_model.objects.get(id=user_id)


class RoleUserMixin:
    request: Request

    @lazyproperty
    def user(self):
        return self.request.user
