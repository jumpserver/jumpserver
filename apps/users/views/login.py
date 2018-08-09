# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals
import os
from django.core.cache import cache
from django.shortcuts import render
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.core.files.storage import default_storage
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import reverse, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from formtools.wizard.views import SessionWizardView
from django.conf import settings

from common.utils import get_object_or_none, get_request_ip
from ..models import User, LoginLog
from ..utils import send_reset_password_mail, check_otp_code, \
    redirect_user_first_login_or_index, get_user_or_tmp_user, \
    set_tmp_user_to_cache, get_password_check_rules, check_password_rules, \
    is_block_login, increase_login_failed_count, clean_failed_count
from ..tasks import write_login_log_async
from .. import forms


__all__ = [
    'UserLoginView', 'UserLoginOtpView', 'UserLogoutView',
    'UserForgotPasswordView', 'UserForgotPasswordSendmailSuccessView',
    'UserResetPasswordView', 'UserResetPasswordSuccessView',
    'UserFirstLoginView', 'LoginLogListView'
]


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginView(FormView):
    template_name = 'users/login.html'
    form_class = forms.UserLoginForm
    form_class_captcha = forms.UserLoginCaptchaForm
    redirect_field_name = 'next'
    key_prefix_captcha = "_LOGIN_INVALID_{}"

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect(redirect_user_first_login_or_index(
                request, self.redirect_field_name)
            )
        request.session.set_test_cookie()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # limit login authentication
        ip = get_request_ip(request)
        username = self.request.POST.get('username')
        if is_block_login(username, ip):
            return self.render_to_response(self.get_context_data(block_login=True))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.request.session.test_cookie_worked():
            return HttpResponse(_("Please enable cookies and try again."))

        set_tmp_user_to_cache(self.request, form.get_user())
        username = form.cleaned_data.get('username')
        ip = get_request_ip(self.request)
        # 登陆成功，清除缓存计数
        clean_failed_count(username, ip)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        # write login failed log
        username = form.cleaned_data.get('username')
        data = {
            'username': username,
            'mfa': LoginLog.MFA_UNKNOWN,
            'reason': LoginLog.REASON_PASSWORD,
            'status': False
        }
        self.write_login_log(data)

        # limit user login failed count
        ip = get_request_ip(self.request)
        increase_login_failed_count(username, ip)

        # show captcha
        cache.set(self.key_prefix_captcha.format(ip), 1, 3600)
        old_form = form
        form = self.form_class_captcha(data=form.data)
        form._errors = old_form.errors
        return super().form_invalid(form)

    def get_form_class(self):
        ip = get_request_ip(self.request)
        if cache.get(self.key_prefix_captcha.format(ip)):
            return self.form_class_captcha
        else:
            return self.form_class

    def get_success_url(self):
        user = get_user_or_tmp_user(self.request)

        if user.otp_enabled and user.otp_secret_key:
            # 1,2,mfa_setting & T
            return reverse('users:login-otp')
        elif user.otp_enabled and not user.otp_secret_key:
            # 1,2,mfa_setting & F
            return reverse('users:user-otp-enable-authentication')
        elif not user.otp_enabled:
            # 0 & T,F
            auth_login(self.request, user)
            data = {
                'username': self.request.user.username,
                'mfa': int(self.request.user.otp_enabled),
                'reason': LoginLog.REASON_NOTHING,
                'status': True
            }
            self.write_login_log(data)
            return redirect_user_first_login_or_index(self.request, self.redirect_field_name)

    def get_context_data(self, **kwargs):
        context = {
            'demo_mode': os.environ.get("DEMO_MODE"),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def write_login_log(self, data):
        login_ip = get_request_ip(self.request)
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        tmp_data = {
            'ip': login_ip,
            'type': 'W',
            'user_agent': user_agent
        }
        data.update(tmp_data)
        write_login_log_async.delay(**data)


class UserLoginOtpView(FormView):
    template_name = 'users/login_otp.html'
    form_class = forms.UserCheckOtpCodeForm
    redirect_field_name = 'next'

    def form_valid(self, form):
        user = get_user_or_tmp_user(self.request)
        otp_code = form.cleaned_data.get('otp_code')
        otp_secret_key = user.otp_secret_key

        if check_otp_code(otp_secret_key, otp_code):
            auth_login(self.request, user)
            data = {
                'username': self.request.user.username,
                'mfa': int(self.request.user.otp_enabled),
                'reason': LoginLog.REASON_NOTHING,
                'status': True
            }
            self.write_login_log(data)
            return redirect(self.get_success_url())
        else:
            data = {
                'username': user.username,
                'mfa': int(user.otp_enabled),
                'reason': LoginLog.REASON_MFA,
                'status': False
            }
            self.write_login_log(data)
            form.add_error('otp_code', _('MFA code invalid, or ntp sync server time'))
            return super().form_invalid(form)

    def get_success_url(self):
        return redirect_user_first_login_or_index(self.request, self.redirect_field_name)

    def write_login_log(self, data):
        login_ip = get_request_ip(self.request)
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        tmp_data = {
            'ip': login_ip,
            'type': 'W',
            'user_agent': user_agent
        }
        data.update(tmp_data)
        write_login_log_async.delay(**data)


@method_decorator(never_cache, name='dispatch')
class UserLogoutView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        response = super().get(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Logout success'),
            'messages': _('Logout success, return login page'),
            'interval': 1,
            'redirect_url': reverse('users:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserForgotPasswordView(TemplateView):
    template_name = 'users/forgot_password.html'

    def post(self, request):
        email = request.POST.get('email')
        user = get_object_or_none(User, email=email)
        if not user:
            return self.get(request, errors=_('Email address invalid, '
                                              'please input again'))
        else:
            send_reset_password_mail(user)
            return HttpResponseRedirect(
                reverse('users:forgot-password-sendmail-success'))


class UserForgotPasswordSendmailSuccessView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Send reset password message'),
            'messages': _('Send reset password mail success, '
                          'login your mail box and follow it '),
            'redirect_url': reverse('users:login'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserResetPasswordSuccessView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Reset password success'),
            'messages': _('Reset password success, return to login page'),
            'redirect_url': reverse('users:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super()\
            .get_context_data(**kwargs)


class UserResetPasswordView(TemplateView):
    template_name = 'users/reset_password.html'

    def get(self, request, *args, **kwargs):
        token = request.GET.get('token')
        user = User.validate_reset_token(token)

        check_rules, min_length = get_password_check_rules()
        password_rules = {'password_check_rules': check_rules, 'min_length': min_length}
        kwargs.update(password_rules)

        if not user:
            kwargs.update({'errors': _('Token invalid or expired')})
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        password = request.POST.get('password')
        password_confirm = request.POST.get('password-confirm')
        token = request.GET.get('token')

        if password != password_confirm:
            return self.get(request, errors=_('Password not same'))

        user = User.validate_reset_token(token)
        if not user:
            return self.get(request, errors=_('Token invalid or expired'))

        is_ok = check_password_rules(password)
        if not is_ok:
            return self.get(
                request,
                errors=_('* Your password does not meet the requirements')
            )

        user.reset_password(password)
        return HttpResponseRedirect(reverse('users:reset-password-success'))


class UserFirstLoginView(LoginRequiredMixin, SessionWizardView):
    template_name = 'users/first_login.html'
    form_list = [
        forms.UserProfileForm,
        forms.UserPublicKeyForm,
        forms.UserMFAForm,
        forms.UserFirstLoginFinishForm
    ]
    file_storage = default_storage

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_first_login:
            return redirect(reverse('index'))
        return super().dispatch(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        user = self.request.user
        for form in form_list:
            for field in form:
                if field.value():
                    setattr(user, field.name, field.value())
        user.is_first_login = False
        user.is_public_key_valid = True
        user.save()
        context = {
            'user_guide_url': settings.USER_GUIDE_URL
        }
        return render(self.request, 'users/first_login_done.html', context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'app': _('Users'), 'action': _('First login')})
        return context

    def get_form_initial(self, step):
        user = self.request.user
        if step == '0':
            return {
                'username': user.username or '',
                'name': user.name or user.username,
                'email': user.email or '',
                'wechat': user.wechat or '',
                'phone': user.phone or ''
            }
        return super().get_form_initial(step)

    def get_form(self, step=None, data=None, files=None):
        form = super().get_form(step, data, files)
        form.instance = self.request.user

        if isinstance(form, forms.UserMFAForm):
            choices = form.fields["otp_level"].choices
            if self.request.user.otp_force_enabled:
                choices = [(k, v) for k, v in choices if k == 2]
            else:
                choices = [(k, v) for k, v in choices if k in [0, 1]]
            form.fields["otp_level"].choices = choices
            form.fields["otp_level"].initial = self.request.user.otp_level

        return form


class LoginLogListView(ListView):
    def get(self, request, *args, **kwargs):
        return redirect(reverse('audits:login-log-list'))
