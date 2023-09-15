# -*- coding: utf-8 -*-
#
from datetime import timedelta
from importlib import import_module

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY
from django.core.cache import caches
from django.dispatch import receiver
from django.utils import timezone, translation
from django.utils.functional import LazyObject
from django.utils.translation import gettext_lazy as _
from rest_framework.request import Request

from audits.models import UserLoginLog
from authentication.signals import post_auth_failed, post_auth_success
from authentication.utils import check_different_city_login_if_need
from common.utils import get_request_ip, get_logger
from users.models import User
from ..const import LoginTypeChoices
from ..models import UserSession
from ..utils import write_login_log

logger = get_logger(__name__)


class AuthBackendLabelMapping(LazyObject):
    @staticmethod
    def get_login_backends():
        backend_label_mapping = {}
        for source, backends in User.SOURCE_BACKEND_MAPPING.items():
            for backend in backends:
                backend_label_mapping[backend] = source.label
        backend_label_mapping[settings.AUTH_BACKEND_PUBKEY] = _("SSH Key")
        backend_label_mapping[settings.AUTH_BACKEND_MODEL] = _("Password")
        backend_label_mapping[settings.AUTH_BACKEND_SSO] = _("SSO")
        backend_label_mapping[settings.AUTH_BACKEND_AUTH_TOKEN] = _("Auth Token")
        backend_label_mapping[settings.AUTH_BACKEND_WECOM] = _("WeCom")
        backend_label_mapping[settings.AUTH_BACKEND_FEISHU] = _("FeiShu")
        backend_label_mapping[settings.AUTH_BACKEND_DINGTALK] = _("DingTalk")
        backend_label_mapping[settings.AUTH_BACKEND_TEMP_TOKEN] = _("Temporary token")
        backend_label_mapping[settings.AUTH_BACKEND_PASSKEY] = _("Passkey")
        return backend_label_mapping

    def _setup(self):
        self._wrapped = self.get_login_backends()


AUTH_BACKEND_LABEL_MAPPING = AuthBackendLabelMapping()


def get_login_backend(request):
    backend = request.session.get('auth_backend', '') or \
              request.session.get(BACKEND_SESSION_KEY, '')

    backend_label = AUTH_BACKEND_LABEL_MAPPING.get(backend, None)
    if backend_label is None:
        backend_label = ''
    return backend_label


def generate_data(username, request, login_type=None):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    login_ip = get_request_ip(request) or '0.0.0.0'

    if login_type is None and isinstance(request, Request):
        login_type = request.META.get('HTTP_X_JMS_LOGIN_TYPE', 'U')
    if login_type is None:
        login_type = 'W'

    with translation.override('en'):
        backend = str(get_login_backend(request))

    data = {
        'username': username,
        'ip': login_ip,
        'type': login_type,
        'user_agent': user_agent[0:254],
        'datetime': timezone.now(),
        'backend': backend,
    }
    return data


def create_user_session(session_key, user_id, instance: UserLoginLog):
    session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
    session_store = session_store_cls(session_key=session_key)
    cache_key = session_store.cache_key
    ttl = caches[settings.SESSION_CACHE_ALIAS].ttl(cache_key)

    online_session_data = {
        'user_id': user_id,
        'ip': instance.ip,
        'key': session_key,
        'city': instance.city,
        'type': instance.type,
        'backend': instance.backend,
        'user_agent': instance.user_agent,
        'date_created': instance.datetime,
        'date_expired': instance.datetime + timedelta(seconds=ttl),
    }
    UserSession.objects.create(**online_session_data)


@receiver(post_auth_success)
def on_user_auth_success(sender, user, request, login_type=None, **kwargs):
    logger.debug('User login success: {}'.format(user.username))
    check_different_city_login_if_need(user, request)
    data = generate_data(
        user.username, request, login_type=login_type
    )
    request.session['login_time'] = data['datetime'].strftime("%Y-%m-%d %H:%M:%S")
    data.update({'mfa': int(user.mfa_enabled), 'status': True})
    instance = write_login_log(**data)
    session_key = request.session.session_key
    # TODO 目前只记录 web 登录的 session
    if not session_key or instance.type != LoginTypeChoices.web:
        return
    create_user_session(session_key, user.id, instance)


@receiver(post_auth_failed)
def on_user_auth_failed(sender, username, request, reason='', **kwargs):
    logger.debug('User login failed: {}'.format(username))
    data = generate_data(username, request)
    data.update({'reason': reason[:128], 'status': False})
    write_login_log(**data)
