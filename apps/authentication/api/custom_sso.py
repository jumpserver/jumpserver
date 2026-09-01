import importlib
import sys
import threading
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.http.response import HttpResponseRedirect
from django.utils.module_loading import import_string
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.utils import get_logger
from rbac.models import SystemRole, SystemRoleBinding
from ..mixins import AuthMixin

__all__ = ['CustomSSOLoginAPIView']

logger = get_logger(__file__)

CUSTOM_SSO_AUTH_METHOD_PATH = 'data.auth.custom_sso.authenticate'
CUSTOM_SSO_AUTH_MODULE_PATH = 'data.auth.custom_sso'
CUSTOM_SSO_IMPORT_RETRY_INTERVAL = 1
CUSTOM_SSO_IMPORT_MAX_WAIT = 5

custom_sso_authenticate_method = None
_custom_sso_import_lock = threading.Lock()
_custom_sso_next_retry_at = 0.0
_custom_sso_last_import_error = ''


class CustomSSOLoadError(Exception):
    pass


def get_custom_sso_authenticate_method():
    """Retry loading for a bounded time, then keep the method immutable."""
    global custom_sso_authenticate_method
    global _custom_sso_next_retry_at
    global _custom_sso_last_import_error

    deadline = time.monotonic() + CUSTOM_SSO_IMPORT_MAX_WAIT

    while True:
        if callable(custom_sso_authenticate_method):
            return custom_sso_authenticate_method

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CustomSSOLoadError(_custom_sso_last_import_error)

        lock_acquired = _custom_sso_import_lock.acquire(timeout=remaining)
        if not lock_acquired:
            raise CustomSSOLoadError(_custom_sso_last_import_error)

        try:
            if callable(custom_sso_authenticate_method):
                return custom_sso_authenticate_method

            now = time.monotonic()
            if now >= deadline:
                raise CustomSSOLoadError(_custom_sso_last_import_error)

            retry_delay = _custom_sso_next_retry_at - now
            if retry_delay <= 0:
                try:
                    importlib.invalidate_caches()
                    method = import_string(CUSTOM_SSO_AUTH_METHOD_PATH)
                    if not callable(method):
                        raise TypeError(
                            f'{CUSTOM_SSO_AUTH_METHOD_PATH} must be callable'
                        )
                except Exception as e:
                    # A successfully imported module with a missing/non-callable
                    # `authenticate` remains in sys.modules. Remove it so a
                    # corrected file can be retried, but never reload after the
                    # first success.
                    sys.modules.pop(CUSTOM_SSO_AUTH_MODULE_PATH, None)
                    custom_sso_authenticate_method = None
                    _custom_sso_last_import_error = str(e)
                    _custom_sso_next_retry_at = (
                        time.monotonic() + CUSTOM_SSO_IMPORT_RETRY_INTERVAL
                    )
                    retry_delay = CUSTOM_SSO_IMPORT_RETRY_INTERVAL
                    logger.warning(
                        'Import custom SSO auth method failed: %s; retrying in '
                        '%s seconds',
                        e,
                        CUSTOM_SSO_IMPORT_RETRY_INTERVAL,
                        exc_info=True,
                    )
                else:
                    custom_sso_authenticate_method = method
                    _custom_sso_next_retry_at = 0.0
                    _custom_sso_last_import_error = ''
                    return custom_sso_authenticate_method
        finally:
            _custom_sso_import_lock.release()

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CustomSSOLoadError(_custom_sso_last_import_error)
        if retry_delay > 0:
            time.sleep(min(retry_delay, remaining))


class CustomSSOLoginAPIView(AuthMixin, RetrieveAPIView):
    permission_classes = [AllowAny]

    next_url = '/'

    @staticmethod
    def is_enabled():
        return settings.AUTH_CUSTOM_SSO

    def retrieve(self, request, *args, **kwargs):
        if not self.is_enabled():
            error = 'Custom SSO authentication is disabled.'
            return Response({'detail': error}, status=status.HTTP_403_FORBIDDEN)

        query_param_names = settings.AUTH_CUSTOM_SSO_QUERY_PARAMS
        if isinstance(query_param_names, str):
            query_param_names = query_param_names.split(',')
        query_param_names = [
            param.strip() for param in query_param_names if param.strip()
        ]

        query_params = {}
        for param in query_param_names:
            value = self.request.query_params.get(param)
            if not value:
                error = f'Missing required query parameter: {param}'
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
            query_params[param] = value

        try:
            authenticate_method = get_custom_sso_authenticate_method()
        except CustomSSOLoadError:
            error = 'Custom SSO authentication is temporarily unavailable.'
            return Response({'detail': error}, status=status.HTTP_403_FORBIDDEN)

        user, error = self.authenticate(authenticate_method, **query_params)
        if user:
            login(request, user, backend=settings.AUTH_BACKEND_CUSTOM_SSO)
            self.send_auth_signal(success=True, user=user)
            return HttpResponseRedirect(self.next_url)
        else:
            self.send_auth_signal(success=False, reason=error)
            return Response({'detail': error}, status=status.HTTP_401_UNAUTHORIZED)

    def authenticate(self, authenticate_method, **query_params):
        try:
            userinfo, error = authenticate_method(**query_params)
            if error:
                return None, error
            self.next_url = userinfo.get('next_url', '/')
        except Exception as e:
            error = f'Custom SSO authenticate error: {e}'
            return None, error

        try:
            user = self.get_or_create_user_from_userinfo(userinfo)
            return user, ''
        except Exception as e:
            error = f'Custom SSO get or create user error: {e}'
            return None, error

    def get_or_create_user_from_userinfo(self, userinfo: dict):
        User = get_user_model()
        username = userinfo.get('username')
        if username == 'admin':
            user = User.objects.filter(username='admin').first()
            return user

        name = userinfo.get('name')
        email = userinfo.get('email')
        defaults = {'name': name, 'email': email}
        user, created = get_user_model().objects.get_or_create(
            username=username, defaults=defaults
        )
        if created:
            system_role_name = userinfo.get('system_role_name')
            system_role = SystemRole.objects.filter(name=system_role_name).first()
            sys_role_binding = SystemRoleBinding(user=user, role=system_role)
            sys_role_binding.save()

        return user
