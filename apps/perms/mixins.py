# ~*~ coding: utf-8 ~*~
#

from orgs.utils import set_to_root_org

__all__ = [
    'ChangeOrgIfNeedMixin',
]


class ChangeOrgIfNeedMixin(object):

    @staticmethod
    def change_org_if_need(request, kwargs):
        if request.user.is_authenticated and request.user.is_superuser \
                or request.user.is_app \
                or kwargs.get('pk') is None:
            set_to_root_org()

    def get(self, request, *args, **kwargs):
        self.change_org_if_need(request, kwargs)
        return super().get(request, *args, **kwargs)
