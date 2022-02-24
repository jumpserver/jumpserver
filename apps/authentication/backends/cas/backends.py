# -*- coding: utf-8 -*-
#
from django_cas_ng.backends import CASBackend as _CASBackend
from django.conf import settings

from ..base import JMSBaseAuthBackend

__all__ = ['CASBackend']


class CASBackend(JMSBaseAuthBackend, _CASBackend):
    @classmethod
    def is_enabled(cls):
        return settings.AUTH_CAS

    def user_can_authenticate(self, user):
        return True

    def has_perm(self, user_obj, perm, obj=None):
        return False
