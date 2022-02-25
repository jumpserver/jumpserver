# -*- coding: utf-8 -*-
#
from django_cas_ng.backends import CASBackend as _CASBackend
from django.conf import settings

from ..base import JMSBaseAuthBackend

__all__ = ['CASBackend']


class CASBackend(JMSBaseAuthBackend, _CASBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_CAS
