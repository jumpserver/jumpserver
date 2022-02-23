# -*- coding: utf-8 -*-
#
from users.models import User


class UserQuerysetMixin:
    def get_queryset(self):
        queryset = User.get_org_users().filter(is_service_account=False)
        return queryset
