from importlib import import_module

from django.conf import settings
from django.contrib.auth import user_logged_in
from django.core.cache import cache
from django.dispatch import receiver
from django_cas_ng.signals import cas_user_authenticated

from apps.jumpserver.settings.auth import AUTHENTICATION_BACKENDS_THIRD_PARTY
from audits.models import UserSession
from .signals import post_auth_success, post_auth_failed, user_auth_failed, user_auth_success


@receiver(user_logged_in)
def on_user_auth_login_success(sender, user, request, **kwargs):
    # 失效 perms 缓存
    user.expire_rbac_perms_cache()

    # 开启了 MFA，且没有校验过, 可以全局校验, middleware 中可以全局管理 oidc 等第三方认证的 MFA
    if settings.SECURITY_MFA_AUTH_ENABLED_FOR_THIRD_PARTY \
            and user.mfa_enabled \
            and not request.session.get('auth_mfa'):
        request.session['auth_mfa_required'] = 1
    if not request.session.get("auth_third_party_done") and \
            request.session.get('auth_backend') in AUTHENTICATION_BACKENDS_THIRD_PARTY:
        request.session['auth_third_party_required'] = 1

    user_session_id = request.session.get('user_session_id')
    UserSession.objects.filter(id=user_session_id).update(key=request.session.session_key)
    # 单点登录，超过了自动退出
    if settings.USER_LOGIN_SINGLE_MACHINE_ENABLED:
        lock_key = 'single_machine_login_' + str(user.id)
        session_key = cache.get(lock_key)
        if session_key and session_key != request.session.session_key:
            session = import_module(settings.SESSION_ENGINE).SessionStore(session_key)
            session.delete()
            UserSession.objects.filter(key=session_key).delete()
        cache.set(lock_key, request.session.session_key, None)


@receiver(cas_user_authenticated)
def on_cas_user_login_success(sender, request, user, **kwargs):
    request.session['auth_backend'] = settings.AUTH_BACKEND_CAS
    post_auth_success.send(sender, user=user, request=request)


@receiver(user_auth_success)
def on_user_login_success(sender, request, user, backend, create=False, **kwargs):
    request.session['auth_backend'] = backend
    post_auth_success.send(sender, user=user, request=request)


@receiver(user_auth_failed)
def on_user_login_failed(sender, username, request, reason, backend, **kwargs):
    request.session['auth_backend'] = backend
    post_auth_failed.send(sender, username=username, request=request, reason=reason)
