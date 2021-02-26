# ~*~ coding: utf-8 ~*~
#

from __future__ import unicode_literals
import os
import datetime
from django.core.cache import cache
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

from common.utils import get_request_ip, get_object_or_none
from users.utils import (
    redirect_user_first_login_or_index
)
from ..const import RSA_PRIVATE_KEY, RSA_PUBLIC_KEY
from .. import mixins, errors, utils
from ..forms import get_user_login_form_cls


__all__ = [
    'UserLoginView', 'UserLogoutView',
    'UserLoginGuardView', 'UserLoginWaitConfirmView',
    'FlashPasswdTooSimpleMsgView', 'FlashPasswdHasExpiredMsgView'
]


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginView(mixins.AuthMixin, FormView):
    key_prefix_captcha = "_LOGIN_INVALID_{}"
    redirect_field_name = 'next'
    template_name = 'authentication/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            first_login_url = redirect_user_first_login_or_index(
                request, self.redirect_field_name
            )
            return redirect(first_login_url)
        request.session.set_test_cookie()
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.request.session.test_cookie_worked():
            return HttpResponse(_("Please enable cookies and try again."))
        try:
            self.check_user_auth(decrypt_passwd=True)
        except errors.AuthFailedError as e:
            e = self.check_is_block(raise_exception=False) or e
            form.add_error(None, e.msg)
            ip = self.get_request_ip()
            cache.set(self.key_prefix_captcha.format(ip), 1, 3600)
            form_cls = get_user_login_form_cls(captcha=True)
            new_form = form_cls(data=form.data)
            new_form._errors = form.errors
            context = self.get_context_data(form=new_form)
            return self.render_to_response(context)
        except (errors.PasswdTooSimple, errors.PasswordRequireResetError) as e:
            return redirect(e.url)
        self.clear_rsa_key()
        return self.redirect_to_guard_view()

    def redirect_to_guard_view(self):
        guard_url = reverse('authentication:login-guard')
        args = self.request.META.get('QUERY_STRING', '')
        if args:
            guard_url = "%s?%s" % (guard_url, args)
        return redirect(guard_url)

    def get_form_class(self):
        ip = get_request_ip(self.request)
        if cache.get(self.key_prefix_captcha.format(ip)):
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

        context = {
            'demo_mode': os.environ.get("DEMO_MODE"),
            'AUTH_OPENID': settings.AUTH_OPENID,
            'AUTH_CAS': settings.AUTH_CAS,
            'rsa_public_key': rsa_public_key,
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
            auth_login(self.request, user)
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
            ticket = get_object_or_none(Ticket, pk=ticket_id)
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
            'interval': 1,
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


@method_decorator(never_cache, name='dispatch')
class FlashPasswdTooSimpleMsgView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        context = {
            'title': _('Please change your password'),
            'messages': _('Your password is too simple, please change it for security'),
            'interval': 5,
            'redirect_url': request.GET.get('redirect_url'),
            'auto_redirect': True,
        }
        return self.render_to_response(context)


@method_decorator(never_cache, name='dispatch')
class FlashPasswdHasExpiredMsgView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        context = {
            'title': _('Please change your password'),
            'messages': _('Your password has expired, please reset before logging in'),
            'interval': 5,
            'redirect_url': request.GET.get('redirect_url'),
            'auto_redirect': True,
        }
        return self.render_to_response(context)
