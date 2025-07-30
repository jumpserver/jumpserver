# -*- coding: utf-8 -*-
#

import threading

from django.conf import settings
from django.contrib.auth import get_user_model
from django_cas_ng.backends import CASBackend as _CASBackend

from common.utils import get_logger
from ..base import JMSBaseAuthBackend

__all__ = ['CASBackend', 'CASUserDoesNotExist']
logger = get_logger(__name__)


class CASUserDoesNotExist(Exception):
    """Exception raised when a CAS user does not exist."""
    pass


class CASBackend(JMSBaseAuthBackend, _CASBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_CAS

    def authenticate(self, request, ticket, service):
        UserModel = get_user_model()
        manager = UserModel._default_manager
        original_get_by_natural_key = manager.get_by_natural_key
        thread_local = threading.local()
        thread_local.thread_id = threading.get_ident()
        logger.debug(f"CASBackend.authenticate: thread_id={thread_local.thread_id}")

        def get_by_natural_key(self, username):
            logger.debug(f"CASBackend.get_by_natural_key: thread_id={threading.get_ident()}, username={username}")
            if threading.get_ident() != thread_local.thread_id:
                return original_get_by_natural_key(username)

            try:
                user = original_get_by_natural_key(username)
            except UserModel.DoesNotExist:
                raise CASUserDoesNotExist(username)
            return user

        try:
            manager.get_by_natural_key = get_by_natural_key.__get__(manager, type(manager))
            user = super().authenticate(request, ticket=ticket, service=service)
        finally:
            manager.get_by_natural_key = original_get_by_natural_key
        return user
