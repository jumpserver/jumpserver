# -*- coding: utf-8 -*-
#
from .. import utils


class UserQuerysetMixin:
    def get_queryset(self):
        queryset = utils.get_current_org_members()
        return queryset
