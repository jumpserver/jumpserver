from django.shortcuts import redirect, reverse
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.conf import settings


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
            'login/mfa', 'mfa/select', 'jsi18n/', '/static/',
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


class SessionCookieMiddleware(MiddlewareMixin):

    @staticmethod
    def process_response(request, response: HttpResponse):
        key = settings.SESSION_COOKIE_NAME_PREFIX_KEY
        value = settings.SESSION_COOKIE_NAME_PREFIX
        if request.COOKIES.get(key) == value:
            return response
        response.set_cookie(key, value)
        return response
