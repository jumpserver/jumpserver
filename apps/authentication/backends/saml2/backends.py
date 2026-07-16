# -*- coding: utf-8 -*-
#
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction

from common.utils import get_logger
from .signals import (
    saml2_create_or_update_user
)
from ..base import RedirectAuthBackend

__all__ = ['SAML2Backend']

logger = get_logger(__name__)


class SAML2Backend(RedirectAuthBackend):
    backend = settings.AUTH_BACKEND_SAML2

    @staticmethod
    def is_enabled():
        return settings.AUTH_SAML2

    @transaction.atomic
    def get_or_create_from_saml_data(self, request, **saml_user_data):
        log_prompt = "Get or Create user [SAML2Backend]: {}"
        logger.debug(log_prompt.format('start'))

        groups = saml_user_data.pop('groups', None)

        user, created = get_user_model().objects.get_or_create(
            username=saml_user_data['username'], defaults=saml_user_data
        )

        saml_user_data['groups'] = groups
        logger.debug(log_prompt.format("user: {}|created: {}".format(user, created)))

        logger.debug(log_prompt.format("Send signal => saml2 create or update user"))
        saml2_create_or_update_user.send(
            sender=self, request=request, user=user, created=created, attrs=saml_user_data
        )
        return user, created

    def authenticate(self, request, saml_user_data=None):
        log_prompt = "Process authenticate [SAML2Backend]: {}"
        logger.debug(log_prompt.format('Start'))
        if saml_user_data is None:
            logger.error(log_prompt.format('saml_user_data is missing'))
            return None

        logger.debug(log_prompt.format('saml data, {}'.format(saml_user_data)))
        username = saml_user_data.get('username')
        if not username:
            logger.warning(log_prompt.format('username is missing'))
            return None

        user, created = self.get_or_create_from_saml_data(request, **saml_user_data)

        if self.user_can_authenticate(user):
            logger.debug(log_prompt.format('SAML2 user login success'))
            return user
        else:
            logger.debug(log_prompt.format('SAML2 user login failed'))
            self.send_backend_auth_failed_signal(request=request, username=user.username)
            return None
