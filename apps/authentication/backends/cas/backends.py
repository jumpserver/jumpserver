# -*- coding: utf-8 -*-
#
from django_cas_ng.backends import CASBackend as _CASBackend

from ..mixins import ModelBackendMixin


__all__ = ['CASBackend']


class CASBackend(ModelBackendMixin, _CASBackend):
    def user_can_authenticate(self, user):
        return True
