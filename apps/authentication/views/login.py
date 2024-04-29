# ~*~ coding: utf-8 ~*~
#

from __future__ import unicode_literals

import datetime
import os
from typing import Callable
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.db import IntegrityError
from django.http import HttpRequest
from django.shortcuts import reverse, redirect
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _, get_language
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import TemplateView, RedirectView
from django.views.generic.edit import FormView

from common.utils import FlashMessageUtil, static_or_direct, safe_next_url
from users.utils import (
    redirect_user_first_login_or_index
)
from .. import mixins, errors
from ..const import RSA_PRIVATE_KEY, RSA_PUBLIC_KEY
from ..forms import get_user_login_form_cls

__all__ = [
    'UserLoginView', 'UserLogoutView',
    'UserLoginGuardView', 'UserLoginWaitConfirmView',
]


class UserLoginContextMixin:
    get_user_mfa_context: Callable
    request: HttpRequest
    error_origin: str

    def get_support_auth_methods(self):
        auth_methods = [
            {
                'name': 'OpenID',
                'enabled': settings.AUTH_OPENID,
                'url': reverse('authentication:openid:login'),
                'logo': static('img/login_oidc_logo.png'),
                'auto_redirect': True  # 是否支持自动重定向
            },
            {
                'name': 'CAS',
                'enabled': settings.AUTH_CAS,
                'url': reverse('authentication:cas:cas-login'),
                'logo': static('img/login_cas_logo.png'),
                'auto_redirect': True
            },
            {
                'name': 'SAML2',
                'enabled': settings.AUTH_SAML2,
                'url': reverse('authentication:saml2:saml2-login'),
                'logo': static('img/login_saml2_logo.png'),
                'auto_redirect': True
            },
            {
                'name': settings.AUTH_OAUTH2_PROVIDER,
                'enabled': settings.AUTH_OAUTH2,
                'url': reverse('authentication:oauth2:login'),
                'logo': static_or_direct(settings.AUTH_OAUTH2_LOGO_PATH),
                'auto_redirect': True
            },
            {
                'name': _('WeCom'),
                'enabled': settings.AUTH_WECOM,
                'url': reverse('authentication:wecom-qr-login'),
                'logo': static('img/login_wecom_logo.png'),
            },
            {
                'name': _('DingTalk'),
                'enabled': settings.AUTH_DINGTALK,
                'url': reverse('authentication:dingtalk-qr-login'),
                'logo': static('img/login_dingtalk_logo.png')
            },
            {
                'name': _('FeiShu'),
                'enabled': settings.AUTH_FEISHU,
                'url': reverse('authentication:feishu-qr-login'),
                'logo': static('img/login_feishu_logo.png')
            },
            {
                'name': 'Lark',
                'enabled': settings.AUTH_LARK,
                'url': reverse('authentication:lark-qr-login'),
                'logo': static('img/login_lark_logo.png')
            },
            {
                'name': _('Slack'),
                'enabled': settings.AUTH_SLACK,
                'url': reverse('authentication:slack-qr-login'),
                'logo': static('img/login_slack_logo.png')
            },
            {
                'name': _("Passkey"),
                'enabled': settings.AUTH_PASSKEY,
                'url': reverse('api-auth:passkey-login'),
                'logo': static('img/login_passkey.png')
            }
        ]
        return [method for method in auth_methods if method['enabled']]

    @staticmethod
    def get_support_langs():
        langs = [
            {
                'title': '中文(简体)',
                'code': 'zh-hans'
            },
            {
                'title': '中文(繁體)',
                'code': 'zh-hant'
            },
            {
                'title': 'English',
                'code': 'en'
            },
            {
                'title': '日本語',
                'code': 'ja'
            }
        ]
        return langs

    def get_current_lang(self):
        langs = self.get_support_langs()
        matched_lang = filter(lambda x: x['code'] == get_language(), langs)
        return next(matched_lang, langs[0])

    @staticmethod
    def get_forgot_password_url():
        forgot_password_url = reverse('authentication:forgot-previewing')
        forgot_password_url = settings.FORGOT_PASSWORD_URL or forgot_password_url
        return forgot_password_url

    def get_extra_fields_count(self, context):
        count = 0
        if self.get_support_auth_methods():
            count += 1
        form = context.get('form')
        if not form:
            return count
        if set(form.fields.keys()) & {'captcha', 'challenge', 'mfa_type'}:
            count += 1
        if form.errors or form.non_field_errors():
            count += 1
        return count

    def set_csrf_error_if_need(self, context):
        if not self.request.GET.get('csrf_failure'):
            return context

        http_origin = self.request.META.get('HTTP_ORIGIN')
        http_referer = self.request.META.get('HTTP_REFERER')
        http_origin = http_origin or http_referer

        if not http_origin:
            return context

        try:
            origin = urlparse(http_origin)
            context['error_origin'] = str(origin.netloc)
        except ValueError:
            pass
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_csrf_error_if_need(context)
        context.update({
            'demo_mode': os.environ.get("DEMO_MODE"),
            'auth_methods': self.get_support_auth_methods(),
            'langs': self.get_support_langs(),
            'current_lang': self.get_current_lang(),
            'forgot_password_url': self.get_forgot_password_url(),
            'extra_fields_count': self.get_extra_fields_count(context),
            **self.get_user_mfa_context(self.request.user)
        })
        return context


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginView(mixins.AuthMixin, UserLoginContextMixin, FormView):
    redirect_field_name = 'next'
    template_name = 'authentication/login.html'

    def redirect_third_party_auth_if_need(self, request):
        # show jumpserver login page if request http://{JUMP-SERVER}/?admin=1
        if self.request.GET.get("admin", 0):
            return None

        if not settings.XPACK_ENABLED:
            return None

        auth_types = [m for m in self.get_support_auth_methods() if m.get('auto_redirect')]
        if not auth_types:
            return None

        # 明确直接登录哪个
        login_to = settings.LOGIN_REDIRECT_TO_BACKEND.upper()
        if login_to == 'DIRECT':
            return None

        auth_method = next(filter(lambda x: x['name'] == login_to, auth_types), None)
        if not auth_method:
            auth_method = auth_types[0]

        auth_name, redirect_url = auth_method['name'], auth_method['url']
        next_url = request.GET.get('next') or '/'
        next_url = safe_next_url(next_url, request=request)
        query_string = request.GET.urlencode()
        redirect_url = '{}?next={}&{}'.format(redirect_url, next_url, query_string)

        if settings.LOGIN_REDIRECT_MSG_ENABLED:
            message_data = {
                'title': _('Redirecting'),
                'message': _("Redirecting to {} authentication").format(auth_name),
                'redirect_url': redirect_url,
                'interval': 3,
                'has_cancel': True,
                'cancel_url': reverse('authentication:login') + '?admin=1'
            }
            redirect_url = FlashMessageUtil.gen_message_url(message_data)
        return redirect_url

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            first_login_url = redirect_user_first_login_or_index(
                request, self.redirect_field_name
            )
            return redirect(first_login_url)
        redirect_url = self.redirect_third_party_auth_if_need(request)
        if redirect_url:
            return redirect(redirect_url)
        request.session.set_test_cookie()
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.request.session.test_cookie_worked():
            form.add_error(None, _("Login timeout, please try again."))
            return self.form_invalid(form)

        # https://docs.djangoproject.com/en/3.1/topics/http/sessions/#setting-test-cookies
        self.request.session.delete_test_cookie()

        try:
            self.check_user_auth(form.cleaned_data)
        except errors.AuthFailedError as e:
            form.add_error(None, e.msg)
            self.set_login_failed_mark()
            form_cls = get_user_login_form_cls(captcha=True)
            new_form = form_cls(data=form.data)
            new_form._errors = form.errors
            context = self.get_context_data(form=new_form)
            self.request.session.set_test_cookie()
            return self.render_to_response(context)
        except errors.NeedRedirectError as e:
            return redirect(e.url)
        except (
                errors.MFAFailedError,
                errors.BlockMFAError,
                errors.MFACodeRequiredError,
                errors.SMSCodeRequiredError,
                errors.UserPhoneNotSet,
                errors.BlockGlobalIpLoginError
        ) as e:
            form.add_error('code', e.msg)
            return super().form_invalid(form)
        except (IntegrityError,) as e:
            # (1062, "Duplicate entry 'youtester001@example.com' for key 'users_user.email'")
            error = str(e)
            if len(e.args) < 2:
                form.add_error(None, error)
                return super().form_invalid(form)

            msg_list = e.args[1].split("'")
            if len(msg_list) < 4:
                form.add_error(None, error)
                return super().form_invalid(form)

            email, field = msg_list[1], msg_list[3]
            if field == 'users_user.email':
                error = _('User email already exists ({})').format(email)
            form.add_error(None, error)
            return super().form_invalid(form)
        self.clear_rsa_key()
        return self.redirect_to_guard_view()

    def get_form_class(self):
        if self.check_is_need_captcha():
            return get_user_login_form_cls(captcha=True)
        else:
            return get_user_login_form_cls()

    def clear_rsa_key(self):
        self.request.session[RSA_PRIVATE_KEY] = None
        self.request.session[RSA_PUBLIC_KEY] = None


class UserLoginGuardView(mixins.AuthMixin, RedirectView):
    redirect_field_name = 'next'
    login_url = reverse_lazy('authentication:login')
    login_mfa_url = reverse_lazy('authentication:login-mfa')
    login_confirm_url = reverse_lazy('authentication:login-wait-confirm')

    def format_redirect_url(self, url):
        args = self.request.META.get('QUERY_STRING', '')
        if args and self.query_string:
            url = "%s?%s" % (url, args)
        return url

    def login_it(self, user):
        auth_login(self.request, user)
        # 如果设置了自动登录，那需要设置 session_id cookie 的有效期
        if self.request.session.get('auto_login'):
            age = self.request.session.get_expiry_age()
            self.request.session.set_expiry(age)

    def get_redirect_url(self, *args, **kwargs):
        try:
            user = self.get_user_from_session()
            self.check_user_mfa_if_need(user)
            self.check_user_login_confirm_if_need(user)
        except (errors.CredentialError, errors.SessionEmptyError) as e:
            print("Error: ", e)
            return self.format_redirect_url(self.login_url)
        except errors.MFARequiredError:
            return self.format_redirect_url(self.login_mfa_url)
        except errors.LoginConfirmBaseError:
            return self.format_redirect_url(self.login_confirm_url)
        except errors.MFAUnsetError as e:
            return e.url
        except errors.PasswordTooSimple as e:
            return e.url
        else:
            self.login_it(user)
            self.send_auth_signal(success=True, user=user)
            self.clear_auth_mark()
            url = redirect_user_first_login_or_index(
                self.request, self.redirect_field_name
            )
            return url


class UserLoginWaitConfirmView(TemplateView):
    template_name = 'authentication/login_wait_confirm.html'

    def get_context_data(self, **kwargs):
        from tickets.models import Ticket
        from tickets.const import TICKET_DETAIL_URL
        ticket_id = self.request.session.get("auth_ticket_id")
        if not ticket_id:
            ticket = None
        else:
            ticket = Ticket.all().filter(pk=ticket_id).first()
        context = super().get_context_data(**kwargs)
        if ticket:
            timestamp_created = datetime.datetime.timestamp(ticket.date_created)
            ticket_detail_url = TICKET_DETAIL_URL.format(id=ticket_id, type=ticket.type)
            assignees_display = ', '.join([str(assignee) for assignee in ticket.current_assignees])
            msg = _("""Wait for <b>{}</b> confirm, You also can copy link to her/him <br/>
                  Don't close this page""").format(assignees_display)
        else:
            timestamp_created = 0
            ticket_detail_url = ''
            msg = _("No ticket found")
        context.update({
            "msg": msg,
            "timestamp": timestamp_created,
            "ticket_detail_url": ticket_detail_url
        })
        return context


@method_decorator(never_cache, name='dispatch')
class UserLogoutView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get_backend_logout_url(self):
        backend = self.request.session.get(BACKEND_SESSION_KEY, '')
        if 'OIDC' in backend:
            return settings.AUTH_OPENID_AUTH_LOGOUT_URL_NAME
        elif 'CAS' in backend:
            return settings.CAS_LOGOUT_URL_NAME
        elif 'saml2' in backend:
            return settings.SAML2_LOGOUT_URL_NAME
        elif 'oauth2' in backend:
            return settings.AUTH_OAUTH2_LOGOUT_URL_NAME
        return None

    def get(self, request, *args, **kwargs):
        backend_logout_url = self.get_backend_logout_url()
        if backend_logout_url:
            return redirect(backend_logout_url)

        auth_logout(request)
        response = super().get(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Logout success'),
            'message': _('Logout success, return login page'),
            'interval': 3,
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
