from collections import defaultdict
from urllib.parse import urljoin

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from common.utils import reverse, get_request_ip_or_data, get_request_user_agent
from common.views.template import custom_render_to_string
from notifications.notifications import UserMessage


class UserCreatedMsg(UserMessage):
    subject = str(settings.EMAIL_CUSTOM_USER_CREATED_SUBJECT)
    template_name = 'users/_msg_user_created.html'
    contexts = [
        {"name": "honorific", "label": _('Honorific'), "default": "zhangsan"},
        {"name": "content", "label": _('Content'), "default": "Welcome to use our system."},
        {"name": "username", "label": _('Username'), "default": "zhangsan"},
        {"name": "name", "label": _('Name'), "default": "张三"},
        {"name": "email", "label": _('Email'), "default": "123456@qq.com"},
        {"name": "rest_password_url", "label": _('Reset password url'),
         "default": "https://example.com/reset-password"},
        {"name": "rest_password_token", "label": _('Reset password token'), "default": "abcdefg1234567"},
        {"name": "forget_password_url", "label": _('Forget password url'),
         "default": "https://example.com/forget-password"},
    ]

    def get_html_msg(self) -> dict:
        user = self.user

        mail_context = {
            'subject': str(settings.EMAIL_CUSTOM_USER_CREATED_SUBJECT),
            'honorific': str(settings.EMAIL_CUSTOM_USER_CREATED_HONORIFIC),
            'content': str(settings.EMAIL_CUSTOM_USER_CREATED_BODY)
        }

        user_info = {'username': user.username, 'name': user.name, 'email': user.email}
        # 转换成 defaultdict，否则 format 时会报 KeyError
        user_info = defaultdict(str, **user_info)
        mail_context = {k: v.format_map(user_info) for k, v in mail_context.items()}

        context = {
            **mail_context,
            **user_info,
            'rest_password_url': reverse('authentication:reset-password', external=True),
            'rest_password_token': user.generate_reset_token(),
            'forget_password_url': reverse('authentication:login', external=True),
        }
        message = custom_render_to_string(self.template_name, context)
        return {
            'subject': mail_context['subject'],
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        user = cls.get_test_user()
        return cls(user)


class ResetPasswordMsg(UserMessage):
    subject = _('Reset password')
    template_name = 'authentication/_msg_reset_password.html'
    contexts = [
        {"name": "email", "label": _('Email'), "default": "123456@qq.com"},
        {"name": "rest_password_url", "label": _('Reset password url'),
         "default": "https://example.com/reset-password"},
        {"name": "rest_password_token", "label": _('Reset password token'), "default": "abcdefg1234567"},
        {"name": "forget_password_url", "label": _('Forget password url'),
         "default": "https://example.com/forget-password"},
        {"name": "login_url", "label": _('Login url'), "default": "https://example.com/login"},
    ]

    def __init__(self, user):
        super().__init__(user)
        self.reset_passwd_token = user.generate_reset_token()

    def get_html_msg(self) -> dict:
        user = self.user
        context = {
            'email': user.email,
            'rest_password_url': reverse('authentication:reset-password', external=True),
            'rest_password_token': self.reset_passwd_token,
            'forget_password_url': reverse('authentication:forgot-password', external=True),
            'login_url': reverse('authentication:login', external=True),
        }
        message = render_to_string('authentication/_msg_reset_password.html', context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        user = User.objects.first()
        return cls(user)


class ResetPasswordSuccessMsg(UserMessage):
    subject = _('Reset password success')
    template_name = 'authentication/_msg_rest_password_success.html'
    contexts = [
        {"name": "name", "label": _('Name'), "default": "张三"},
        {"name": "ip_address", "label": _('IP address'), "default": "192.168.1.1"},
        {"name": "browser", "label": _('Browser'), "default": "Mozilla/firefox"}
    ]

    def __init__(self, user, request):
        super().__init__(user)
        self.ip_address = get_request_ip_or_data(request)
        self.browser = get_request_user_agent(request)

    def get_html_msg(self) -> dict:
        user = self.user

        context = {
            'name': user.name,
            'ip_address': self.ip_address,
            'browser': self.browser,
        }
        message = custom_render_to_string(self.template_name, context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        from rest_framework.test import APIRequestFactory
        from rest_framework.request import Request
        factory = APIRequestFactory()
        request = Request(factory.get('/notes/'))
        user = User.objects.first()
        return cls(user, request)


class ResetPublicKeySuccessMsg(UserMessage):
    subject = _('Reset public key success')
    template_name = 'authentication/_msg_rest_public_key_success.html'
    contexts = [
        {"name": "name", "label": _('Name'), "default": "张三"},
        {"name": "ip_address", "label": _('IP address'), "default": "192.168.1.1"},
        {"name": "browser", "label": _('Browser'), "default": "Mozilla/firefox"}
    ]

    def __init__(self, user, request):
        super().__init__(user)
        self.ip_address = get_request_ip_or_data(request)
        self.browser = get_request_user_agent(request)

    def get_html_msg(self) -> dict:
        user = self.user

        context = {
            'name': user.name,
            'ip_address': self.ip_address,
            'browser': self.browser,
        }
        message = custom_render_to_string(self.template_name, context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        from rest_framework.test import APIRequestFactory
        from rest_framework.request import Request
        factory = APIRequestFactory()
        request = Request(factory.get('/notes/'))
        user = User.objects.first()
        return cls(user, request)


class PasswordExpirationReminderMsg(UserMessage):
    subject = _('Password is about expire')
    template_name = 'users/_msg_password_expire_reminder.html'
    contexts = [
        {"name": "name", "label": _('Name'), "default": "张三"},
        {"name": "date_password_expired", "label": _('Password expiration date'), "default": "2025-01-01 12:00:00"},
        {"name": "update_password_url", "label": _('Update password url'),
         "default": "https://example.com/update-password"},
        {"name": "forget_password_url", "label": _('Login url'), "default": "https://example.com/forget-password"},
        {"name": "email", "label": _('Email'), "default": "123456@qq.com"},
        {"name": "login_url", "label": _('Login url'), "default": "https://example.com/login"},
    ]

    def get_html_msg(self) -> dict:
        user = self.user

        date_password_expired_local = timezone.localtime(user.date_password_expired)
        update_password_url = urljoin(settings.SITE_URL, '/ui/#/profile/index')
        date_password_expired = date_password_expired_local.strftime('%Y-%m-%d %H:%M:%S')
        context = {
            'name': user.name,
            'date_password_expired': date_password_expired,
            'update_password_url': update_password_url,
            'forget_password_url': reverse('authentication:forgot-password', external=True),
            'email': user.email,
            'login_url': reverse('authentication:login', external=True),
        }
        message = custom_render_to_string(self.template_name, context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        user = User.objects.get(username='admin')
        return cls(user)


class UserExpirationReminderMsg(UserMessage):
    subject = _('Account is about expire')
    template_name = 'users/_msg_account_expire_reminder.html'
    contexts = [
        {"name": "name", "label": _('Name'), "default": "张三"},
        {"name": "date_expired", "label": _('Expiration date'), "default": "2025-01-01 12:00:00"}
    ]

    def get_html_msg(self) -> dict:
        date_expired_local = timezone.localtime(self.user.date_expired)
        date_expired = date_expired_local.strftime('%Y-%m-%d %H:%M:%S')
        context = {
            'name': self.user.name,
            'date_expired': date_expired
        }
        message = render_to_string(self.template_name, context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        user = User.objects.get(username='admin')
        return cls(user)


class ResetSSHKeyMsg(UserMessage):
    subject = _('Reset SSH Key')
    template_name = 'users/_msg_reset_ssh_key.html'
    contexts = [
        {"name": "name", "label": _('Name'), "default": "张三"},
        {"name": "url", "label": _('Update SSH Key url'), "default": "https://example.com/profile/password-and-ssh-key"}
    ]

    def get_html_msg(self) -> dict:
        update_url = urljoin(settings.SITE_URL, '/ui/#/profile/password-and-ssh-key/?tab=SSHKey')
        context = {
            'name': self.user.name,
            'url': update_url,
        }
        message = custom_render_to_string(self.template_name, context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        user = User.objects.get(username='admin')
        return cls(user)


class ResetMFAMsg(UserMessage):
    subject = _('Reset MFA')
    template_name = 'users/_msg_reset_mfa.html'
    contexts = [
        {"name": "name", "label": _('Name'), "default": "张三"},
        {"name": "url", "label": _('Reset MFA url'), "default": "https://example.com/profile/mfa"}
    ]

    def get_html_msg(self) -> dict:
        context = {
            'name': self.user.name,
            'url': reverse('authentication:user-otp-enable-start', external=True),
        }
        message = custom_render_to_string('users/_msg_reset_mfa.html', context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        user = User.objects.get(username='admin')
        return cls(user)
