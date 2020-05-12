# -*- coding: utf-8 -*-
#
from .. import utils
from users.models import User


class UserQuerysetMixin:
    def get_queryset(self):
        if self.request.query_params.get('all'):
            queryset = User.objects.exclude(role=User.ROLE_APP)
        else:
            queryset = utils.get_current_org_members()
        return queryset
