from rest_framework.request import Request

from users.models import User
from perms.utils.user_permission import UserPermTreeUtil
from common.http import is_true


__all__ = ['RebuildTreeMixin']


class RebuildTreeMixin:
    user: User

    def get(self, request: Request, *args, **kwargs):
        force = is_true(request.query_params.get('rebuild_tree'))
        UserPermTreeUtil(self.user).refresh_if_need(force)
        return super().get(request, *args, **kwargs)
