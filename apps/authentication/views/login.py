# ~*~ coding: utf-8 ~*~
#

from __future__ import unicode_literals
import os
import datetime
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import HttpResponse
from django.shortcuts import reverse, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import TemplateView, RedirectView
from django.views.generic.edit import FormView
from django.conf import settings
from django.urls import reverse_lazy
from django.contrib.auth import BACKEND_SESSION_KEY

from common.utils import get_request_ip, FlashMessageUtil
from users.utils import (
    redirect_user_first_login_or_index
)
from ..const import RSA_PRIVATE_KEY, RSA_PUBLIC_KEY
from .. import mixins, errors, utils
from ..forms import get_user_login_form_cls


__all__ = [
    'UserLoginView', 'UserLogoutView',
    'UserLoginGuardView', 'UserLoginWaitConfirmView',
]


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginView(mixins.AuthMixin, FormView):
    redirect_field_name = 'next'
    template_name = 'authentication/login.html'

    def redirect_third_party_auth_if_need(self, request):
        # show jumpserver login page if request http://{JUMP-SERVER}/?admin=1
        if self.request.GET.get("admin", 0):
            return None
        next_url = request.GET.get('next') or '/'
        auth_type = ''
        auth_url = ''
        if settings.AUTH_OPENID:
            auth_type = 'OIDC'
            auth_url = reverse(settings.AUTH_OPENID_AUTH_LOGIN_URL_NAME) + f'?next={next_url}'
        elif settings.AUTH_CAS:
            auth_type = 'CAS'
            auth_url = reverse(settings.CAS_LOGIN_URL_NAME) + f'?next={next_url}'
        if not auth_url:
            return None

        message_data = {
            'title': _('Redirecting'),
            'message': _("Redirecting to {} authentication").format(auth_type),
            'redirect_url': auth_url,
            'has_cancel': True,
            'cancel_url': reverse('authentication:login') + '?admin=1'
        }
        redirect_url = FlashMessageUtil.gen_message_url(message_data)
        query_string = request.GET.urlencode()
        redirect_url = "{}&{}".format(redirect_url, query_string)
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
            return HttpResponse(_("Please enable cookies and try again."))
        # https://docs.djangoproject.com/en/3.1/topics/http/sessions/#setting-test-cookies
        self.request.session.delete_test_cookie()

        try:
            self.check_user_auth(decrypt_passwd=True)
        except errors.AuthFailedError as e:
            form.add_error(None, e.msg)
            self.set_login_failed_mark()

            form_cls = get_user_login_form_cls(captcha=True)
            new_form = form_cls(data=form.data)
            new_form._errors = form.errors
            context = self.get_context_data(form=new_form)
            self.request.session.set_test_cookie()
            return self.render_to_response(context)
        except (errors.PasswdTooSimple, errors.PasswordRequireResetError, errors.PasswdNeedUpdate) as e:
            return redirect(e.url)
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

    def get_context_data(self, **kwargs):
        # 生成加解密密钥对，public_key传递给前端，private_key存入session中供解密使用
        rsa_private_key = self.request.session.get(RSA_PRIVATE_KEY)
        rsa_public_key = self.request.session.get(RSA_PUBLIC_KEY)
        if not all((rsa_private_key, rsa_public_key)):
            rsa_private_key, rsa_public_key = utils.gen_key_pair()
            rsa_public_key = rsa_public_key.replace('\n', '\\n')
            self.request.session[RSA_PRIVATE_KEY] = rsa_private_key
            self.request.session[RSA_PUBLIC_KEY] = rsa_public_key

        forgot_password_url = reverse('authentication:forgot-password')
        has_other_auth_backend = settings.AUTHENTICATION_BACKENDS[0] != settings.AUTH_BACKEND_MODEL
        if has_other_auth_backend and settings.FORGOT_PASSWORD_URL:
            forgot_password_url = settings.FORGOT_PASSWORD_URL

        context = {
            'demo_mode': os.environ.get("DEMO_MODE"),
            'AUTH_OPENID': settings.AUTH_OPENID,
            'AUTH_CAS': settings.AUTH_CAS,
            'AUTH_WECOM': settings.AUTH_WECOM,
            'AUTH_DINGTALK': settings.AUTH_DINGTALK,
            'rsa_public_key': rsa_public_key,
            'forgot_password_url': forgot_password_url
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserLoginGuardView(mixins.AuthMixin, RedirectView):
    redirect_field_name = 'next'
    login_url = reverse_lazy('authentication:login')
    login_otp_url = reverse_lazy('authentication:login-otp')
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
            user = self.check_user_auth_if_need()
            self.check_user_mfa_if_need(user)
            self.check_user_login_confirm_if_need(user)
        except (errors.CredentialError, errors.SessionEmptyError):
            return self.format_redirect_url(self.login_url)
        except errors.MFARequiredError:
            return self.format_redirect_url(self.login_otp_url)
        except errors.LoginConfirmBaseError:
            return self.format_redirect_url(self.login_confirm_url)
        except errors.MFAUnsetError as e:
            return e.url
        except errors.PasswdTooSimple as e:
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
            ticket_detail_url = TICKET_DETAIL_URL.format(id=ticket_id)
            msg = _("""Wait for <b>{}</b> confirm, You also can copy link to her/him <br/>
                  Don't close this page""").format(ticket.assignees_display)
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
            'messages': _('Logout success, return login page'),
            'interval': 3,
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
