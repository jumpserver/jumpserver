# -*- coding: utf-8 -*-
#
import inspect
from urllib.parse import urlencode
from functools import partial
import time

from django.core.cache import cache
from django.conf import settings
from django.contrib import auth
from django.utils.translation import ugettext as _
from django.contrib.auth import (
    BACKEND_SESSION_KEY, _get_backends,
    PermissionDenied, user_login_failed, _clean_credentials
)
from django.shortcuts import reverse, redirect

from common.utils import get_object_or_none, get_request_ip, get_logger, bulk_get, FlashMessageUtil
from users.models import User
from users.utils import LoginBlockUtil, MFABlockUtils
from . import errors
from .utils import rsa_decrypt
from .signals import post_auth_success, post_auth_failed
from .const import RSA_PRIVATE_KEY

logger = get_logger(__name__)


def check_backend_can_auth(username, backend_path, allowed_auth_backends):
    if allowed_auth_backends is not None and backend_path not in allowed_auth_backends:
        logger.debug('Skip user auth backend: {}, {} not in'.format(
                username, backend_path, ','.join(allowed_auth_backends)
            )
        )
        return False
    return True


def authenticate(request=None, **credentials):
    """
    If the given credentials are valid, return a User object.
    """
    username = credentials.get('username')
    allowed_auth_backends = User.get_user_allowed_auth_backends(username)

    for backend, backend_path in _get_backends(return_tuples=True):
        # 预先检查，不浪费认证时间
        if not check_backend_can_auth(username, backend_path, allowed_auth_backends):
            continue

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
        # 如果是 None, 证明没有检查过, 需要再次检查
        if allowed_auth_backends is None:
            # 有些 authentication 参数中不带 username, 之后还要再检查
            allowed_auth_backends = user.get_allowed_auth_backends()
            if not check_backend_can_auth(user.username, backend_path, allowed_auth_backends):
                continue

        # Annotate the user object with the path of the backend.
        user.backend = backend_path
        return user

    # The credentials supplied are invalid to all backends, fire signal
    user_login_failed.send(sender=__name__, credentials=_clean_credentials(credentials), request=request)


auth.authenticate = authenticate


class AuthMixin:
    request = None
    partial_credential_error = None

    key_prefix_captcha = "_LOGIN_INVALID_{}"

    def get_user_from_session(self):
        if self.request.session.is_empty():
            raise errors.SessionEmptyError()

        if all((self.request.user,
                not self.request.user.is_anonymous,
                BACKEND_SESSION_KEY in self.request.session)):
            user = self.request.user
            user.backend = self.request.session[BACKEND_SESSION_KEY]
            return user

        user_id = self.request.session.get('user_id')
        if not user_id:
            user = None
        else:
            user = get_object_or_none(User, pk=user_id)
        if not user:
            raise errors.SessionEmptyError()
        user.backend = self.request.session.get("auth_backend")
        return user

    def get_request_ip(self):
        ip = ''
        if hasattr(self.request, 'data'):
            ip = self.request.data.get('remote_addr', '')
        ip = ip or get_request_ip(self.request)
        return ip

    def _check_is_block(self, username, raise_exception=True):
        ip = self.get_request_ip()
        if LoginBlockUtil(username, ip).is_block():
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

    def decrypt_passwd(self, raw_passwd):
        # 获取解密密钥，对密码进行解密
        rsa_private_key = self.request.session.get(RSA_PRIVATE_KEY)
        if rsa_private_key is not None:
            try:
                return rsa_decrypt(raw_passwd, rsa_private_key)
            except Exception as e:
                logger.error(e, exc_info=True)
                logger.error(f'Decrypt password failed: password[{raw_passwd}] '
                             f'rsa_private_key[{rsa_private_key}]')
                return None
        return raw_passwd

    def raise_credential_error(self, error):
        raise self.partial_credential_error(error=error)

    def _set_partial_credential_error(self, username, ip, request):
        self.partial_credential_error = partial(errors.CredentialError, username=username, ip=ip, request=request)

    def get_auth_data(self, decrypt_passwd=False):
        request = self.request
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request.POST

        items = ['username', 'password', 'challenge', 'public_key', 'auto_login']
        username, password, challenge, public_key, auto_login = bulk_get(data, *items,  default='')
        password = password + challenge.strip()
        ip = self.get_request_ip()
        self._set_partial_credential_error(username=username, ip=ip, request=request)

        if decrypt_passwd:
            password = self.decrypt_passwd(password)
            if not password:
                self.raise_credential_error(errors.reason_password_decrypt_failed)
        return username, password, public_key, ip, auto_login

    def _check_only_allow_exists_user_auth(self, username):
        # 仅允许预先存在的用户认证
        if settings.ONLY_ALLOW_EXIST_USER_AUTH:
            exist = User.objects.filter(username=username).exists()
            if not exist:
                logger.error(f"Only allow exist user auth, login failed: {username}")
                self.raise_credential_error(errors.reason_user_not_exist)

    def _check_auth_user_is_valid(self, username, password, public_key):
        user = authenticate(self.request, username=username, password=password, public_key=public_key)
        if not user:
            self.raise_credential_error(errors.reason_password_failed)
        elif user.is_expired:
            self.raise_credential_error(errors.reason_user_expired)
        elif not user.is_active:
            self.raise_credential_error(errors.reason_user_inactive)
        return user

    def _check_login_acl(self, user, ip):
        # ACL 限制用户登录
        from acls.models import LoginACL
        is_allowed = LoginACL.allow_user_to_login(user, ip)
        if not is_allowed:
            raise errors.LoginIPNotAllowed(username=user.username, request=self.request)

    def set_login_failed_mark(self):
        ip = self.get_request_ip()
        cache.set(self.key_prefix_captcha.format(ip), 1, 3600)

    def set_passwd_verify_on_session(self, user: User):
        self.request.session['user_id'] = str(user.id)
        self.request.session['auth_password'] = 1
        self.request.session['auth_password_expired_at'] = time.time() + settings.AUTH_EXPIRED_SECONDS

    def check_is_need_captcha(self):
        # 最近有登录失败时需要填写验证码
        ip = get_request_ip(self.request)
        need = cache.get(self.key_prefix_captcha.format(ip))
        return need

    def check_user_auth(self, decrypt_passwd=False):
        self.check_is_block()
        request = self.request
        username, password, public_key, ip, auto_login = self.get_auth_data(decrypt_passwd=decrypt_passwd)

        self._check_only_allow_exists_user_auth(username)
        user = self._check_auth_user_is_valid(username, password, public_key)
        # 校验login-acl规则
        self._check_login_acl(user, ip)
        self._check_password_require_reset_or_not(user)
        self._check_passwd_is_too_simple(user, password)
        self._check_passwd_need_update(user)

        LoginBlockUtil(username, ip).clean_failed_count()
        request.session['auth_password'] = 1
        request.session['user_id'] = str(user.id)
        request.session['auto_login'] = auto_login
        request.session['auth_backend'] = getattr(user, 'backend', settings.AUTH_BACKEND_MODEL)
        return user

    def _check_is_local_user(self, user: User):
        if user.source != User.Source.local:
            raise self.raise_credential_error(error=errors.only_local_users_are_allowed)

    def check_oauth2_auth(self, user: User, auth_backend):
        ip = self.get_request_ip()
        request = self.request

        self._set_partial_credential_error(user.username, ip, request)

        if user.is_expired:
            self.raise_credential_error(errors.reason_user_expired)
        elif not user.is_active:
            self.raise_credential_error(errors.reason_user_inactive)

        self._check_is_local_user(user)
        self._check_is_block(user.username)
        self._check_login_acl(user, ip)

        LoginBlockUtil(user.username, ip).clean_failed_count()
        MFABlockUtils(user.username, ip).clean_failed_count()

        request.session['auth_password'] = 1
        request.session['user_id'] = str(user.id)
        request.session['auth_backend'] = auth_backend
        return user

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
            raise errors.PasswdTooSimple(url)

    @classmethod
    def _check_passwd_need_update(cls, user: User):
        if user.need_update_password:
            message = _('You should to change your password before login')
            url = cls.generate_reset_password_url_with_flash_msg(user, message)
            raise errors.PasswdNeedUpdate(url)

    @classmethod
    def _check_password_require_reset_or_not(cls, user: User):
        if user.password_has_expired:
            message = _('Your password has expired, please reset before logging in')
            url = cls.generate_reset_password_url_with_flash_msg(user, message)
            raise errors.PasswordRequireResetError(url)

    def check_user_auth_if_need(self, decrypt_passwd=False):
        request = self.request
        if request.session.get('auth_password') and \
                request.session.get('user_id'):
            user = self.get_user_from_session()
            if user:
                return user
        return self.check_user_auth(decrypt_passwd=decrypt_passwd)

    def check_user_mfa_if_need(self, user):
        if self.request.session.get('auth_mfa'):
            return
        if not user.mfa_enabled:
            return
        unset, url = user.mfa_enabled_but_not_set()
        if unset:
            raise errors.MFAUnsetError(user, self.request, url)
        raise errors.MFARequiredError()

    def mark_mfa_ok(self):
        self.request.session['auth_mfa'] = 1
        self.request.session['auth_mfa_time'] = time.time()
        self.request.session['auth_mfa_type'] = 'otp'

    def check_mfa_is_block(self, username, ip, raise_exception=True):
        if MFABlockUtils(username, ip).is_block():
            logger.warn('Ip was blocked' + ': ' + username + ':' + ip)
            exception = errors.BlockMFAError(username=username, request=self.request, ip=ip)
            if raise_exception:
                raise exception
            else:
                return exception

    def check_user_mfa(self, code):
        user = self.get_user_from_session()
        ip = self.get_request_ip()
        self.check_mfa_is_block(user.username, ip)
        ok = user.check_mfa(code)
        if ok:
            self.mark_mfa_ok()
            return

        raise errors.MFAFailedError(
            username=user.username,
            request=self.request,
            ip=ip
        )

    def get_ticket(self):
        from tickets.models import Ticket
        ticket_id = self.request.session.get("auth_ticket_id")
        logger.debug('Login confirm ticket id: {}'.format(ticket_id))
        if not ticket_id:
            ticket = None
        else:
            ticket = Ticket.all().filter(id=ticket_id).first()
        return ticket

    def get_ticket_or_create(self, confirm_setting):
        ticket = self.get_ticket()
        if not ticket or ticket.status_closed:
            ticket = confirm_setting.create_confirm_ticket(self.request)
            self.request.session['auth_ticket_id'] = str(ticket.id)
        return ticket

    def check_user_login_confirm(self):
        ticket = self.get_ticket()
        if not ticket:
            raise errors.LoginConfirmOtherError('', "Not found")
        if ticket.status_open:
            raise errors.LoginConfirmWaitError(ticket.id)
        elif ticket.action_approve:
            self.request.session["auth_confirm"] = "1"
            return
        elif ticket.action_reject:
            raise errors.LoginConfirmOtherError(
                ticket.id, ticket.get_action_display()
            )
        elif ticket.action_close:
            raise errors.LoginConfirmOtherError(
                ticket.id, ticket.get_action_display()
            )
        else:
            raise errors.LoginConfirmOtherError(
                ticket.id, ticket.get_status_display()
            )

    def check_user_login_confirm_if_need(self, user):
        if not settings.LOGIN_CONFIRM_ENABLE:
            return
        confirm_setting = user.get_login_confirm_setting()
        if self.request.session.get('auth_confirm') or not confirm_setting:
            return
        self.get_ticket_or_create(confirm_setting)
        self.check_user_login_confirm()

    def clear_auth_mark(self):
        self.request.session['auth_password'] = ''
        self.request.session['auth_user_id'] = ''
        self.request.session['auth_mfa'] = ''
        self.request.session['auth_confirm'] = ''
        self.request.session['auth_ticket_id'] = ''

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
