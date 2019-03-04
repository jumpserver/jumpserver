# coding:utf-8
#

from django.contrib.auth import get_user_model
from django.conf import settings

from common.utils import get_logger
from .utils import new_client
from .models import OIDT_ACCESS_TOKEN

UserModel = get_user_model()

logger = get_logger(__file__)
client = new_client()


__all__ = [
    'OpenIDAuthorizationCodeBackend', 'OpenIDAuthorizationPasswordBackend',
]


class BaseOpenIDAuthorizationBackend(object):

    @staticmethod
    def user_can_authenticate(user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

        return user if self.user_can_authenticate(user) else None


class OpenIDAuthorizationCodeBackend(BaseOpenIDAuthorizationBackend):

    def authenticate(self, request, **kwargs):
        logger.info('[OpenID code backend]: '
                    'Authenticate by: {}'.format(self.__class__))

        code = kwargs.get('code')
        redirect_uri = kwargs.get('redirect_uri')

        if not code or not redirect_uri:
            msg = '[OpenID code backend]: ' \
                  'Authenticate failed: No code or No redirect uri'
            logger.info(msg)
            return None

        try:
            oidt_profile = client.update_or_create_from_code(
                    code=code, redirect_uri=redirect_uri
            )

        except Exception as e:
            msg = '[OpenID code backend]: ' \
                  'Authenticate failed: get oidt_profile: {}'.format(e)
            logger.info(msg)

        else:
            # Check openid user single logout or not with access_token
            request.session[OIDT_ACCESS_TOKEN] = oidt_profile.access_token
            user = oidt_profile.user
            msg = '[OpenID code backend]: ' \
                  'Authenticate success: user -> {}'.format(user)
            logger.info(msg)
            return user if self.user_can_authenticate(user) else None


class OpenIDAuthorizationPasswordBackend(BaseOpenIDAuthorizationBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.info('[OpenID password backend]: '
                    'Authenticate by: {}'.format(self.__class__))

        if not settings.AUTH_OPENID:
            msg = '[OpenID password backend]: ' \
                  'Authenticate failed: AUTH_OPENID is False'
            logger.info(msg)
            return None
        elif not username:
            msg = '[OpenID password backend]: Authenticate failed: Not username'
            logger.info(msg)
            return None

        try:
            oidt_profile = client.update_or_create_from_password(
                username=username, password=password
            )

        except Exception as e:
            msg = '[OpenID password backend]: ' \
                  'Authenticate failed: get oidt_profile: {}'.format(e)
            logger.info(msg)

        else:
            user = oidt_profile.user
            msg = '[OpenID password backend]: ' \
                  'Authenticate success: user -> {}'.format(user)
            logger.info(msg)
            return user if self.user_can_authenticate(user) else None

