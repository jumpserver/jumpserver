# -*- coding: utf-8 -*-
#
from .. import utils
from users.models import User

from orgs.utils import current_org


class UserQuerysetMixin:
    def get_queryset(self):
        if self.request.query_params.get('all') or current_org.is_root():
            queryset = User.objects.exclude(role=User.ROLE.APP)
        else:
            queryset = utils.get_current_org_members()
        return queryset
