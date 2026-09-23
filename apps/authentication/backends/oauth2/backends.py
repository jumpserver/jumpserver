# -*- coding: utf-8 -*-
#
import base64

import requests

from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils.http import urlencode
from django.conf import settings
from django.urls import reverse

from common.utils import get_logger
from users.utils import construct_user_email
from authentication.backends.http import TLSConfigurationError
from authentication.utils import build_absolute_uri
from common.exceptions import JMSException

from .signals import (
    oauth2_create_or_update_user
)
from .http import OAUTH2_HTTP_TIMEOUT, create_oauth2_session
from ..base import RedirectAuthBackend


__all__ = ['OAuth2Backend']

logger = get_logger(__name__)


class OAuth2Backend(RedirectAuthBackend):
    backend = settings.AUTH_BACKEND_OAUTH2

    @staticmethod
    def is_enabled():
        return settings.AUTH_OAUTH2

    def get_or_create_user_from_userinfo(self, request, userinfo):
        log_prompt = "Get or Create user [OAuth2Backend]: {}"
        logger.debug(log_prompt.format('start'))

        # Construct user attrs value
        user_attrs = {}
        for field, attr in settings.AUTH_OAUTH2_USER_ATTR_MAP.items():
            user_attrs[field] = userinfo.get(attr, '')

        username = user_attrs.get('username')
        if not username:
            error_msg = 'username is missing'
            logger.error(log_prompt.format(error_msg))
            raise JMSException(error_msg)

        email = user_attrs.get('email', '')
        email = construct_user_email(user_attrs.get('username'), email)
        user_attrs.update({'email': email})

        logger.debug(log_prompt.format(user_attrs))
        user, created = get_user_model().objects.get_or_create(
            username=username, defaults=user_attrs
        )
        logger.debug(log_prompt.format("user: {}|created: {}".format(user, created)))
        logger.debug(log_prompt.format("Send signal => oauth2 create or update user"))
        oauth2_create_or_update_user.send(
            sender=self.__class__, request=request, user=user, created=created,
            attrs=user_attrs
        )
        return user, created

    @staticmethod
    def get_response_data(response_data):
        if response_data.get('data') is not None:
            response_data = response_data['data']
        return response_data

    @staticmethod
    def request_json(session, stage, method, url, **kwargs):
        try:
            response = session.request(
                method, url, timeout=OAUTH2_HTTP_TIMEOUT, **kwargs
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                logger.error('OAuth2 %s response must be a JSON object', stage)
                return None
            return data
        except requests.exceptions.Timeout:
            logger.error('OAuth2 %s request timed out', stage)
        except requests.exceptions.SSLError:
            logger.error('OAuth2 %s TLS certificate verification failed', stage)
        except requests.exceptions.RequestException as error:
            logger.error(
                'OAuth2 %s request failed (%s)', stage, error.__class__.__name__
            )
        except (TypeError, ValueError):
            logger.error('OAuth2 %s response is not valid JSON', stage)
        return None

    def authenticate(self, request, code=None, state=None):
        log_prompt = "Process authenticate [OAuth2Backend]: {}"
        logger.debug(log_prompt.format('Start'))
        if code is None:
            logger.error(log_prompt.format('code is missing'))
            return None

        if settings.AUTH_OAUTH2_USE_STATE:
            if state is None:
                logger.error(log_prompt.format('state is missing'))
                return None

            session_state = request.session.get('oauth2_state')
            if not session_state or session_state != state:
                logger.error(log_prompt.format('state parameter mismatch'))
                return None

            request.session.pop('oauth2_state', None)

        query_dict = {
            'grant_type': 'authorization_code', 'code': code,
            'redirect_uri': build_absolute_uri(
                request, path=reverse(settings.AUTH_OAUTH2_AUTH_LOGIN_CALLBACK_URL_NAME)
            )
        }
        separator = '&' if '?' in settings.AUTH_OAUTH2_ACCESS_TOKEN_ENDPOINT else '?'
        access_token_url = '{url}{separator}{query}'.format(
            url=settings.AUTH_OAUTH2_ACCESS_TOKEN_ENDPOINT,
            separator=separator, query=urlencode(query_dict)
        )
        # token_method -> get, post(post_data), post_json
        token_method = settings.AUTH_OAUTH2_ACCESS_TOKEN_METHOD.lower()
        logger.debug(log_prompt.format('Call the access token endpoint[method: %s]' % token_method))
        encoded_credentials = base64.b64encode(
            f"{settings.AUTH_OAUTH2_CLIENT_ID}:{settings.AUTH_OAUTH2_CLIENT_SECRET}".encode()
        ).decode()
        headers = {
            'Accept': 'application/json', 'Authorization': f'Basic {encoded_credentials}'
        }
        try:
            session = create_oauth2_session()
        except TLSConfigurationError:
            logger.error('OAuth2 TLS configuration is invalid')
            return None

        with session:
            if token_method.startswith('post'):
                body_key = 'json' if token_method.endswith('json') else 'data'
                query_dict.update({
                    'client_id': settings.AUTH_OAUTH2_CLIENT_ID,
                    'client_secret': settings.AUTH_OAUTH2_CLIENT_SECRET,
                })
                request_data = {body_key: query_dict}
            else:
                request_data = {}

            access_token_response_data = self.request_json(
                session, 'token', token_method.split('_')[0],
                access_token_url, headers=headers, **request_data
            )
            if access_token_response_data is None:
                return None
            response_data = self.get_response_data(access_token_response_data)
            if not isinstance(response_data, dict):
                logger.error('OAuth2 token response data must be a JSON object')
                return None

            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer {}'.format(response_data.get('access_token', ''))
            }
            logger.debug(log_prompt.format('Get userinfo endpoint'))
            userinfo_response_data = self.request_json(
                session, 'userinfo', 'get',
                settings.AUTH_OAUTH2_PROVIDER_USERINFO_ENDPOINT, headers=headers
            )
            if userinfo_response_data is None:
                return None
            userinfo = self.get_response_data(userinfo_response_data)
            if not isinstance(userinfo, dict):
                logger.error('OAuth2 userinfo response data must be a JSON object')
                return None

        try:
            logger.debug(log_prompt.format('Update or create oauth2 user'))
            user, created = self.get_or_create_user_from_userinfo(request, userinfo)
        except JMSException:
            return None

        if self.user_can_authenticate(user):
            logger.debug(log_prompt.format('OAuth2 user login success'))
            return user
        else:
            logger.debug(log_prompt.format('OAuth2 user login failed'))
            logger.debug(log_prompt.format('Send signal => oauth2 user login failed'))
            self.send_backend_auth_failed_signal(request=request, username=user.username)
            return None
