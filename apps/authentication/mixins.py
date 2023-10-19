# -*- coding: utf-8 -*-
#
import inspect
import time
from functools import partial
from typing import Callable

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import (
    BACKEND_SESSION_KEY, load_backend,
    PermissionDenied, user_login_failed, _clean_credentials,
)
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import reverse, redirect, get_object_or_404
from django.utils.http import urlencode
from django.utils.translation import gettext as _
from rest_framework.request import Request

from acls.models import LoginACL
from common.utils import get_request_ip_or_data, get_request_ip, get_logger, bulk_get, FlashMessageUtil
from users.models import User
from users.utils import LoginBlockUtil, MFABlockUtils, LoginIpBlockUtil
from . import errors
from .signals import post_auth_success, post_auth_failed

logger = get_logger(__name__)


def _get_backends(return_tuples=False):
    backends = []
    for backend_path in settings.AUTHENTICATION_BACKENDS:
        backend = load_backend(backend_path)
        # 检查 backend 是否启用
        if not backend.is_enabled():
            continue
        backends.append((backend, backend_path) if return_tuples else backend)
    if not backends:
        raise ImproperlyConfigured(
            'No authentication backends have been defined. Does '
            'AUTHENTICATION_BACKENDS contain anything?'
        )
    return backends


auth._get_backends = _get_backends


def authenticate(request=None, **credentials):
    """
    If the given credentials are valid, return a User object.
    之所以 hack 这个 auticate
    """
    username = credentials.get('username')

    temp_user = None
    for backend, backend_path in _get_backends(return_tuples=True):
        # 检查用户名是否允许认证 (预先检查，不浪费认证时间)
        logger.info('Try using auth backend: {}'.format(str(backend)))
        if not backend.username_allow_authenticate(username):
            continue

        # 原生
        backend_signature = inspect.signature(backend.authenticate)
        try:
            backend_signature.bind(request, **credentials)
        except TypeError:
            # This backend doesn't accept these credentials as arguments. Try the next one.
            continue
        try:
            user = backend.authenticate(request, **credentials)
        except PermissionDenied:
            # This backend says to stop in our tracks - this user should not be allowed in at all.
            break
        if user is None:
            continue

        if not user.is_valid:
            temp_user = user
            temp_user.backend = backend_path
            request.error_message = _('User is invalid')
            return temp_user

        # 检查用户是否允许认证
        if not backend.user_allow_authenticate(user):
            temp_user = user
            temp_user.backend = backend_path
            continue

        # Annotate the user object with the path of the backend.
        user.backend = backend_path
        return user
    else:
        if temp_user is not None:
            source_display = temp_user.source_display
            request.error_message = _('''The administrator has enabled 'Only allow login from user source'. 
            The current user source is {}. Please contact the administrator.''').format(source_display)
            return temp_user

    # The credentials supplied are invalid to all backends, fire signal
    user_login_failed.send(sender=__name__, credentials=_clean_credentials(credentials), request=request)


auth.authenticate = authenticate


class CommonMixin:
    request: Request
    _ip = ''

    def get_request_ip(self):
        if not self._ip:
            self._ip = get_request_ip_or_data(self.request)
        return self._ip

    def raise_credential_error(self, error):
        raise self.partial_credential_error(error=error)

    def _set_partial_credential_error(self, username, ip, request):
        self.partial_credential_error = partial(
            errors.CredentialError, username=username,
            ip=ip, request=request
        )

    def get_user_from_session(self):
        if self.request.session.is_empty():
            raise errors.SessionEmptyError()

        if all([
            self.request.user,
            not self.request.user.is_anonymous,
            BACKEND_SESSION_KEY in self.request.session
        ]):
            user = self.request.user
            user.backend = self.request.session[BACKEND_SESSION_KEY]
            return user

        user_id = self.request.session.get('user_id')
        auth_ok = self.request.session.get('auth_password')
        auth_expired_at = self.request.session.get('auth_password_expired_at')
        auth_expired = auth_expired_at < time.time() if auth_expired_at else False

        if not user_id or not auth_ok or auth_expired:
            raise errors.SessionEmptyError()

        user = get_object_or_404(User, pk=user_id)
        user.backend = self.request.session.get("auth_backend")
        return user

    def get_auth_data(self, data):
        request = self.request

        items = ['username', 'password', 'challenge', 'public_key', 'auto_login']
        username, password, challenge, public_key, auto_login = bulk_get(data, items, default='')
        ip = self.get_request_ip()
        self._set_partial_credential_error(username=username, ip=ip, request=request)
        password = password + challenge.strip()
        return username, password, public_key, ip, auto_login


class AuthPreCheckMixin:
    request: Request
    get_request_ip: Callable
    raise_credential_error: Callable

    def _check_is_block(self, username, raise_exception=True):
        ip = self.get_request_ip()

        if LoginIpBlockUtil(ip).is_block():
            raise errors.BlockGlobalIpLoginError(username=username, ip=ip)

        is_block = LoginBlockUtil(username, ip).is_block()
        if not is_block:
            return
        logger.warn('Ip was blocked' + ': ' + username + ':' + ip)
        exception = errors.BlockLoginError(username=username, ip=ip)
        if raise_exception:
            raise errors.BlockLoginError(username=username, ip=ip)
        else:
            return exception

    def check_is_block(self, raise_exception=True):
        if hasattr(self.request, 'data'):
            username = self.request.data.get("username")
        else:
            username = self.request.POST.get("username")

        self._check_is_block(username, raise_exception)

    def _check_only_allow_exists_user_auth(self, username):
        # 仅允许预先存在的用户认证
        if not settings.ONLY_ALLOW_EXIST_USER_AUTH:
            return

        exist = User.objects.filter(username=username).exists()
        if not exist:
            logger.error(f"Only allow exist user auth, login failed: {username}")
            self.raise_credential_error(errors.reason_user_not_exist)


class MFAMixin:
    request: Request
    get_user_from_session: Callable
    get_request_ip: Callable

    def _check_if_no_active_mfa(self, user):
        active_mfa_mapper = user.active_mfa_backends_mapper
        if not active_mfa_mapper:
            set_url = reverse('authentication:user-otp-enable-start')
            raise errors.MFAUnsetError(set_url, user, self.request)

    def _check_login_page_mfa_if_need(self, user):
        if not settings.SECURITY_MFA_IN_LOGIN_PAGE:
            return
        if not user.active_mfa_backends:
            return

        request = self.request
        data = request.data if hasattr(request, 'data') else request.POST
        code = data.get('code')
        mfa_type = data.get('mfa_type', 'otp')

        if not code:
            return
        self._do_check_user_mfa(code, mfa_type, user=user)

    def check_user_mfa_if_need(self, user):
        if self.request.session.get('auth_mfa') and \
                self.request.session.get('auth_mfa_username') == user.username:
            return
        if not user.mfa_enabled:
            return

        active_mfa_names = user.active_mfa_backends_mapper.keys()
        raise errors.MFARequiredError(mfa_types=tuple(active_mfa_names))

    def mark_mfa_ok(self, mfa_type, user):
        self.request.session['auth_mfa'] = 1
        self.request.session['auth_mfa_username'] = user.username
        self.request.session['auth_mfa_time'] = time.time()
        self.request.session['auth_mfa_required'] = 0
        self.request.session['auth_mfa_type'] = mfa_type
        MFABlockUtils(user.username, self.get_request_ip()).clean_failed_count()

    def clean_mfa_mark(self):
        keys = ['auth_mfa', 'auth_mfa_time', 'auth_mfa_required', 'auth_mfa_type', 'auth_mfa_username']
        for k in keys:
            self.request.session.pop(k, '')

    def check_mfa_is_block(self, username, ip, raise_exception=True):
        blocked = MFABlockUtils(username, ip).is_block()
        if not blocked:
            return
        logger.warn('Ip was blocked' + ': ' + username + ':' + ip)
        exception = errors.BlockMFAError(username=username, request=self.request, ip=ip)
        if raise_exception:
            raise exception
        else:
            return exception

    def _do_check_user_mfa(self, code, mfa_type, user=None):
        user = user if user else self.get_user_from_session()
        if not user.mfa_enabled:
            return

        # 监测 MFA 是不是屏蔽了
        ip = self.get_request_ip()
        self.check_mfa_is_block(user.username, ip)

        ok = False
        mfa_backend = user.get_mfa_backend_by_type(mfa_type)
        backend_error = _('The MFA type ({}) is not enabled')
        if not mfa_backend:
            msg = backend_error.format(mfa_type)
        elif not mfa_backend.is_active():
            msg = backend_error.format(mfa_backend.display_name)
        else:
            ok, msg = mfa_backend.check_code(code)

        if ok:
            self.mark_mfa_ok(mfa_type, user)
            return

        raise errors.MFAFailedError(
            username=user.username,
            request=self.request,
            ip=ip, mfa_type=mfa_type,
            error=msg
        )

    @staticmethod
    def get_user_mfa_context(user=None):
        mfa_backends = User.get_user_mfa_backends(user)
        return {'mfa_backends': mfa_backends}

    @staticmethod
    def incr_mfa_failed_time(username, ip):
        util = MFABlockUtils(username, ip)
        util.incr_failed_count()


class AuthPostCheckMixin:
    @classmethod
    def generate_reset_password_url_with_flash_msg(cls, user, message):
        reset_passwd_url = reverse('authentication:reset-password')
        query_str = urlencode({
            'token': user.generate_reset_token()
        })
        reset_passwd_url = f'{reset_passwd_url}?{query_str}'

        message_data = {
            'title': _('Please change your password'),
            'message': message,
            'interval': 3,
            'redirect_url': reset_passwd_url,
        }
        return FlashMessageUtil.gen_message_url(message_data)

    @classmethod
    def _check_passwd_is_too_simple(cls, user: User, password):
        if user.is_superuser and password == 'admin':
            message = _('Your password is too simple, please change it for security')
            url = cls.generate_reset_password_url_with_flash_msg(user, message=message)
            raise errors.PasswordTooSimple(url)

    @classmethod
    def _check_passwd_need_update(cls, user: User):
        if user.need_update_password:
            message = _('You should to change your password before login')
            url = cls.generate_reset_password_url_with_flash_msg(user, message)
            raise errors.PasswordNeedUpdate(url)

    @classmethod
    def _check_password_require_reset_or_not(cls, user: User):
        if user.password_has_expired:
            message = _('Your password has expired, please reset before logging in')
            url = cls.generate_reset_password_url_with_flash_msg(user, message)
            raise errors.PasswordRequireResetError(url)


class AuthACLMixin:
    request: Request
    get_request_ip: Callable

    def _check_login_acl(self, user, ip):
        # ACL 限制用户登录
        acl = LoginACL.get_match_rule_acls(user, ip)
        if not acl:
            return

        if acl.is_action(LoginACL.ActionChoices.accept):
            return

        if acl.is_action(LoginACL.ActionChoices.reject):
            raise errors.LoginACLIPAndTimePeriodNotAllowed(user.username, request=self.request)

        if acl.is_action(acl.ActionChoices.review):
            self.request.session['auth_confirm_required'] = '1'
            self.request.session['auth_acl_id'] = str(acl.id)
            return

        if acl.is_action(acl.ActionChoices.notice):
            self.request.session['auth_notice_required'] = '1'
            self.request.session['auth_acl_id'] = str(acl.id)
            return

    def _check_third_party_login_acl(self):
        request = self.request
        error_message = getattr(request, 'error_message', None)
        if not error_message:
            return
        raise ValueError(error_message)

    def check_user_login_confirm_if_need(self, user):
        if not self.request.session.get("auth_confirm_required"):
            return
        acl_id = self.request.session.get('auth_acl_id')
        logger.debug('Login confirm acl id: {}'.format(acl_id))
        if not acl_id:
            return

        acl = LoginACL.get_user_acls(user).filter(id=acl_id).first()
        if not acl:
            return
        if not acl.is_action(acl.ActionChoices.review):
            return
        self.get_ticket_or_create(acl, user)
        self.check_user_login_confirm()

    def get_ticket_or_create(self, acl, user):
        ticket = self.get_ticket()
        if not ticket or ticket.is_state(ticket.State.closed):
            ticket = acl.create_confirm_ticket(self.request, user)
            self.request.session['auth_ticket_id'] = str(ticket.id)
        return ticket

    def check_user_login_confirm(self):
        ticket = self.get_ticket()
        if not ticket:
            raise errors.LoginConfirmOtherError('', "Not found", '')
        elif ticket.is_state(ticket.State.approved):
            self.request.session["auth_confirm_required"] = ''
            return
        elif ticket.is_status(ticket.Status.open):
            raise errors.LoginConfirmWaitError(ticket.id)
        else:
            # rejected, closed
            ticket_id = ticket.id
            status = ticket.get_state_display()
            username = ticket.applicant.username
            raise errors.LoginConfirmOtherError(ticket_id, status, username)

    def get_ticket(self):
        from tickets.models import ApplyLoginTicket
        ticket_id = self.request.session.get("auth_ticket_id")
        logger.debug('Login confirm ticket id: {}'.format(ticket_id))
        if not ticket_id:
            ticket = None
        else:
            ticket = ApplyLoginTicket.all().filter(id=ticket_id).first()
        return ticket


class AuthMixin(CommonMixin, AuthPreCheckMixin, AuthACLMixin, MFAMixin, AuthPostCheckMixin):
    request = None
    partial_credential_error = None

    key_prefix_captcha = "_LOGIN_INVALID_{}"

    def _check_auth_user_is_valid(self, username, password, public_key):
        user = authenticate(
            self.request, username=username,
            password=password, public_key=public_key
        )
        if not user:
            self.raise_credential_error(errors.reason_password_failed)

        self.request.session['auth_backend'] = getattr(user, 'backend', settings.AUTH_BACKEND_MODEL)

        if user.is_expired:
            self.raise_credential_error(errors.reason_user_expired)
        elif not user.is_active:
            self.raise_credential_error(errors.reason_user_inactive)
        return user

    def set_login_failed_mark(self):
        ip = self.get_request_ip()
        cache.set(self.key_prefix_captcha.format(ip), 1, 3600)

    def check_is_need_captcha(self):
        # 最近有登录失败时需要填写验证码
        ip = get_request_ip(self.request)
        need = cache.get(self.key_prefix_captcha.format(ip))
        return need

    def check_user_auth(self, valid_data=None):
        # pre check
        self.check_is_block()
        username, password, public_key, ip, auto_login = self.get_auth_data(valid_data)
        self._check_only_allow_exists_user_auth(username)

        # check auth
        user = self._check_auth_user_is_valid(username, password, public_key)

        # 校验login-acl规则
        self._check_login_acl(user, ip)

        # post check
        self._check_password_require_reset_or_not(user)
        self._check_passwd_is_too_simple(user, password)
        self._check_passwd_need_update(user)
        user.cache_login_password_if_need(password)

        # 校验login-mfa, 如果登录页面上显示 mfa 的话
        self._check_login_page_mfa_if_need(user)

        # 标记密码验证成功
        self.mark_password_ok(user=user, auto_login=auto_login)
        LoginBlockUtil(user.username, ip).clean_failed_count()
        LoginIpBlockUtil(ip).clean_block_if_need()
        return user

    def mark_password_ok(self, user, auto_login=False, auth_backend=None):
        request = self.request
        request.session['auth_password'] = 1
        request.session['auth_password_expired_at'] = time.time() + settings.AUTH_EXPIRED_SECONDS
        request.session['user_id'] = str(user.id)
        request.session['auto_login'] = auto_login
        if not auth_backend:
            auth_backend = getattr(user, 'backend', settings.AUTH_BACKEND_MODEL)

        request.session['auth_backend'] = auth_backend

    def check_oauth2_auth(self, user: User, auth_backend):
        ip = self.get_request_ip()
        request = self.request

        self._set_partial_credential_error(user.username, ip, request)

        if user.is_expired:
            self.raise_credential_error(errors.reason_user_expired)
        elif not user.is_active:
            self.raise_credential_error(errors.reason_user_inactive)

        self._check_is_block(user.username)
        self._check_login_acl(user, ip)

        LoginBlockUtil(user.username, ip).clean_failed_count()
        LoginIpBlockUtil(ip).clean_block_if_need()
        MFABlockUtils(user.username, ip).clean_failed_count()

        self.mark_password_ok(user, False, auth_backend)
        return user

    def get_user_or_auth(self, valid_data):
        request = self.request
        if request.session.get('auth_password'):
            return self.get_user_from_session()
        else:
            return self.check_user_auth(valid_data)

    def clear_auth_mark(self):
        keys = [
            'auth_password', 'user_id', 'auth_confirm_required',
            'auth_notice_required', 'auth_ticket_id', 'auth_acl_id',
            'user_session_id', 'user_log_id', 'can_send_notifications'
        ]
        for k in keys:
            self.request.session.pop(k, '')

    def send_auth_signal(self, success=True, user=None, username='', reason=''):
        if success:
            post_auth_success.send(
                sender=self.__class__, user=user, request=self.request
            )
        else:
            post_auth_failed.send(
                sender=self.__class__, username=username,
                request=self.request, reason=reason
            )

    def redirect_to_guard_view(self):
        guard_url = reverse('authentication:login-guard')
        args = self.request.META.get('QUERY_STRING', '')
        if args:
            guard_url = "%s?%s" % (guard_url, args)
        return redirect(guard_url)
