from django.core.cache import cache

from rest_framework.request import Request

from common.utils.http import is_true
from common.utils import lazyproperty
from perms.utils import UserPermTreeRefreshUtil
from users.models import User

__all__ = ['RebuildTreeMixin']


class RebuildTreeMixin:
    user: User
    request: Request

    def get(self, request, *args, **kwargs):
        UserPermTreeRefreshUtil(self.user).refresh_if_need(force=self.is_force_refresh_tree)
        return super().get(request, *args, **kwargs)

    @lazyproperty
    def is_force_refresh_tree(self):
        force = is_true(self.request.query_params.get('rebuild_tree'))
        if not force:
            force = self.compute_is_force_refresh()
        return force

    def compute_is_force_refresh(self):
        """ 5s 内连续刷新三次转为强制刷新 """
        force_timeout = 5
        force_max_count = 3
        force_cache_key = '{user_id}:{path}'.format(user_id=self.user.id, path=self.request.path)
        count = cache.get(force_cache_key, 1)
        if count >= force_max_count:
            force = True
            cache.delete(force_cache_key)
        else:
            force = False
            cache.set(force_cache_key, count + 1, force_timeout)
        return force
