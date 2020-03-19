# -*- coding: utf-8 -*-
#
from django_cas_ng.backends import CASBackend as _CASBackend


__all__ = ['CASBackend']


class CASBackend(_CASBackend):
    def user_can_authenticate(self, user):
        return True
