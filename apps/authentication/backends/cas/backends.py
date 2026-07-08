# -*- coding: utf-8 -*-
#

from django.conf import settings
from django_cas_ng.backends import CASBackend as _CASBackend

from common.utils import get_logger
from ..base import RedirectAuthBackend

__all__ = ['CASBackend']
logger = get_logger(__name__)


class CASBackend(RedirectAuthBackend, _CASBackend):
    backend = settings.AUTH_BACKEND_CAS

    @staticmethod
    def is_enabled():
        return settings.AUTH_CAS

    def authenticate(self, request, ticket, service):
        # 这里做个hack ,让父类始终走CAS_CREATE_USER=True的逻辑，然后调用 authentication/mixins.py 中的 custom_get_or_create 方法
        settings.CAS_CREATE_USER = True
        user = super().authenticate(request, ticket, service)
        if user is None:
            self.send_backend_auth_failed_signal(request=request)
        return user
