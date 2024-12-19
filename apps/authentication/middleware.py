import base64

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect, reverse, render
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext as _

from apps.authentication import mixins
from audits.signal_handlers import send_login_info_to_reviewers
from authentication.signals import post_auth_failed
from common.utils import gen_key_pair
from common.utils import get_request_ip


class MFAMiddleware:
    """
    这个 中间件 是用来全局拦截开启了 MFA 却没有认证的，如 OIDC, CAS，使用第三方库做的登录，直接 login 了，
    所以只能在 Middleware 中控制
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # 没有校验
        if not request.session.get('auth_mfa_required'):
            return response
        # 没有认证过，证明不是从 第三方 来的
        if request.user.is_anonymous:
            return response

        # 这个是 mfa 登录页需要的请求, 也得放出来, 用户其实已经在 CAS/OIDC 中完成登录了
        white_urls = [
            'login/mfa', 'mfa/select', 'face/context','jsi18n/', '/static/',
            '/profile/otp', '/logout/',
        ]
        for url in white_urls:
            if request.path.find(url) > -1:
                return response

        # 因为使用 CAS/OIDC 登录的，不小心去了别的页面就回不来了
        if request.path.find('users/profile') > -1:
            return HttpResponse('', status=401)

        url = reverse('authentication:login-mfa') + '?_=middleware'
        return redirect(url)


class ThirdPartyLoginMiddleware(mixins.AuthMixin):
    """OpenID、CAS、SAML2登录规则设置验证"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # 没有认证过，证明不是从 第三方 来的
        if request.user.is_anonymous:
            return response
        if not request.session.get('auth_third_party_required'):
            return response
        white_urls = [
            'jsi18n/', '/static/',
            'login/guard', 'login/wait-confirm',
            'login-confirm-ticket/status',
            'settings/public/open',
            'core/auth/login', 'core/auth/logout'
        ]
        for url in white_urls:
            if request.path.find(url) > -1:
                return response

        ip = get_request_ip(request)
        try:
            self.request = request
            self._check_third_party_login_acl()
            self._check_login_acl(request.user, ip)
        except Exception as e:
            if getattr(request, 'user_need_delete', False):
                request.user.delete()
            else:
                error_message = getattr(e, 'msg', None)
                error_message = error_message or str(e)
                post_auth_failed.send(
                    sender=self.__class__, username=request.user.username,
                    request=self.request, reason=error_message
                )
            auth_logout(request)
            context = {
                'title': _('Authentication failed'),
                'message': _('Authentication failed (before login check failed): {}').format(e),
                'interval': 10,
                'redirect_url': reverse('authentication:login') + '?admin=1',
                'auto_redirect': True,
            }
            response = render(request, 'authentication/auth_fail_flash_message_standalone.html', context)
        else:
            if not self.request.session.get('auth_confirm_required'):
                return response
            guard_url = reverse('authentication:login-guard')
            args = request.META.get('QUERY_STRING', '')
            if args:
                guard_url = "%s?%s" % (guard_url, args)
            response = redirect(guard_url)
        finally:
            if request.session.get('can_send_notifications') and \
                    self.request.session.get('auth_notice_required'):
                request.session['can_send_notifications'] = False
                user_log_id = self.request.session.get('user_log_id')
                auth_acl_id = self.request.session.get('auth_acl_id')
                send_login_info_to_reviewers(user_log_id, auth_acl_id)
            return response


class SessionCookieMiddleware(MiddlewareMixin):
    USER_LOGIN_ENCRYPTION_KEY_PAIR = 'user_login_encryption_key_pair'

    def set_cookie_public_key(self, request, response):
        if request.path.startswith('/api'):
            return

        session_public_key_name = settings.SESSION_RSA_PUBLIC_KEY_NAME
        session_private_key_name = settings.SESSION_RSA_PRIVATE_KEY_NAME

        session_public_key = request.session.get(session_public_key_name)
        cookie_public_key = request.COOKIES.get(session_public_key_name)

        if session_public_key and session_public_key == cookie_public_key:
            return

        private_key, public_key = self.get_key_pair()

        public_key_decode = base64.b64encode(public_key.encode()).decode()

        request.session[session_public_key_name] = public_key_decode
        request.session[session_private_key_name] = private_key
        response.set_cookie(session_public_key_name, public_key_decode)

    def get_key_pair(self):
        key_pair = cache.get(self.USER_LOGIN_ENCRYPTION_KEY_PAIR)
        if key_pair:
            return key_pair['private_key'], key_pair['public_key']

        private_key, public_key = gen_key_pair()

        key_pair = {
            'private_key': private_key,
            'public_key': public_key
        }
        cache.set(self.USER_LOGIN_ENCRYPTION_KEY_PAIR, key_pair, None)

        return private_key, public_key

    @staticmethod
    def set_cookie_session_prefix(request, response):
        key = settings.SESSION_COOKIE_NAME_PREFIX_KEY
        value = settings.SESSION_COOKIE_NAME_PREFIX
        if request.COOKIES.get(key) == value:
            return response
        response.set_cookie(key, value)

    def process_response(self, request, response: HttpResponse):
        self.set_cookie_session_prefix(request, response)
        self.set_cookie_public_key(request, response)
        return response
