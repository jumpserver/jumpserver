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

from common.utils import get_request_ip, get_object_or_none
from users.utils import (
    redirect_user_first_login_or_index
)
from .. import forms, mixins, errors


__all__ = [
    'UserLoginView', 'UserLogoutView',
    'UserLoginGuardView', 'UserLoginWaitConfirmView',
]


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginView(mixins.AuthMixin, FormView):
    form_class = forms.UserLoginForm
    form_class_captcha = forms.UserLoginCaptchaForm
    key_prefix_captcha = "_LOGIN_INVALID_{}"
    redirect_field_name = 'next'

    def get_template_names(self):
        template_name = 'authentication/login.html'
        if not settings.XPACK_ENABLED:
            return template_name

        from xpack.plugins.license.models import License
        if not License.has_valid_license():
            return template_name

        template_name = 'authentication/xpack_login.html'
        return template_name

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect(redirect_user_first_login_or_index(
                request, self.redirect_field_name)
            )
        # show jumpserver login page if request http://{JUMP-SERVER}/?admin=1
        if settings.AUTH_OPENID and not self.request.GET.get('admin', 0):
            query_string = request.GET.urlencode()
            openid_login_url = reverse_lazy("authentication:openid:openid-login")
            login_url = "{}?{}".format(openid_login_url, query_string)
            return redirect(login_url)
        request.session.set_test_cookie()
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.request.session.test_cookie_worked():
            return HttpResponse(_("Please enable cookies and try again."))
        try:
            self.check_user_auth()
        except errors.AuthFailedError as e:
            form.add_error(None, e.msg)
            ip = self.get_request_ip()
            cache.set(self.key_prefix_captcha.format(ip), 1, 3600)
            new_form = self.form_class_captcha(data=form.data)
            new_form._errors = form.errors
            context = self.get_context_data(form=new_form)
            return self.render_to_response(context)
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
            return self.form_class_captcha
        else:
            return self.form_class

    def get_context_data(self, **kwargs):
        context = {
            'demo_mode': os.environ.get("DEMO_MODE"),
            'AUTH_OPENID': settings.AUTH_OPENID,
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
        except errors.CredentialError:
            return self.format_redirect_url(self.login_url)
        except errors.MFARequiredError:
            return self.format_redirect_url(self.login_otp_url)
        except errors.LoginConfirmBaseError:
            return self.format_redirect_url(self.login_confirm_url)
        else:
            auth_login(self.request, user)
            self.send_auth_signal(success=True, user=user)
            self.clear_auth_mark()
            # 启用但是没有设置otp, 排除radius
            if user.mfa_enabled_but_not_set():
                # 1,2,mfa_setting & F
                return reverse('users:user-otp-enable-authentication')
            url = redirect_user_first_login_or_index(
                self.request, self.redirect_field_name
            )
            return url


class UserLoginWaitConfirmView(TemplateView):
    template_name = 'authentication/login_wait_confirm.html'

    def get_context_data(self, **kwargs):
        from tickets.models import Ticket
        ticket_id = self.request.session.get("auth_ticket_id")
        if not ticket_id:
            ticket = None
        else:
            ticket = get_object_or_none(Ticket, pk=ticket_id)
        context = super().get_context_data(**kwargs)
        if ticket:
            timestamp_created = datetime.datetime.timestamp(ticket.date_created)
            ticket_detail_url = reverse('tickets:ticket-detail', kwargs={'pk': ticket_id})
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

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        next_uri = request.COOKIES.get("next")
        if next_uri:
            return redirect(next_uri)
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



