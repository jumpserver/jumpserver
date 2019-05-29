# ~*~ coding: utf-8 ~*~
#
from __future__ import unicode_literals
import os
import re
import pyotp
import base64
import logging

import ipaddress
from django.http import Http404
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth import authenticate
from django.utils.translation import ugettext as _
from django.core.cache import cache
from datetime import datetime

from common.tasks import send_mail_async
from common.utils import reverse, get_object_or_none, get_ip_city
from .models import User


logger = logging.getLogger('jumpserver')


class AdminUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        elif not self.request.user.is_superuser:
            self.raise_exception = True
            return False
        return True


def construct_user_created_email_body(user):
    default_body = _("""
        <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
        <p style="text-indent:2em;">
            <span>
                Username: %(username)s.
            </span>
            <span>
                <a href="%(rest_password_url)s?token=%(rest_password_token)s">click here to set your password</a>
            </span>    
            <span>
                This link is valid for 1 hour. After it expires, <a href="%(forget_password_url)s?email=%(email)s">request new one</a>
            </span> 
            <span>
                <a href="%(login_url)s">Login direct</a>
            </span>
        </p>
        """) % {
        'username': user.username,
        'rest_password_url': reverse('users:reset-password', external=True),
        'rest_password_token': user.generate_reset_token(),
        'forget_password_url': reverse('users:forgot-password', external=True),
        'email': user.email,
        'login_url': reverse('authentication:login', external=True),
    }

    if settings.EMAIL_CUSTOM_USER_CREATED_BODY:
        custom_body = '<p style="text-indent:2em">' + settings.EMAIL_CUSTOM_USER_CREATED_BODY + '</p>'
    else:
        custom_body = ''
    body = custom_body + default_body
    return body


def send_user_created_mail(user):
    recipient_list = [user.email]
    subject = _('Create account successfully')
    if settings.EMAIL_CUSTOM_USER_CREATED_SUBJECT:
        subject = settings.EMAIL_CUSTOM_USER_CREATED_SUBJECT

    honorific = '<p>' + _('Hello %(name)s') % {'name': user.name} + ':</p>'
    if settings.EMAIL_CUSTOM_USER_CREATED_HONORIFIC:
        honorific = '<p>' + settings.EMAIL_CUSTOM_USER_CREATED_HONORIFIC + ':</p>'

    body = construct_user_created_email_body(user)

    signature = '<p style="float:right">jumpserver</p>'
    if settings.EMAIL_CUSTOM_USER_CREATED_SIGNATURE:
        signature = '<p style="float:right">' + settings.EMAIL_CUSTOM_USER_CREATED_SIGNATURE + '</p>'

    message = honorific + body + signature
    if settings.DEBUG:
        try:
            print(message)
        except OSError:
            pass

    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_reset_password_mail(user):
    subject = _('Reset password')
    recipient_list = [user.email]
    message = _("""
    Hello %(name)s:
    </br>
    Please click the link below to reset your password, if not your request, concern your account security
    </br>
    <a href="%(rest_password_url)s?token=%(rest_password_token)s">Click here reset password</a>
    </br>
    This link is valid for 1 hour. After it expires, <a href="%(forget_password_url)s?email=%(email)s">request new one</a>

    </br>
    ---

    </br>
    <a href="%(login_url)s">Login direct</a>

    </br>
    """) % {
        'name': user.name,
        'rest_password_url': reverse('users:reset-password', external=True),
        'rest_password_token': user.generate_reset_token(),
        'forget_password_url': reverse('users:forgot-password', external=True),
        'email': user.email,
        'login_url': reverse('authentication:login', external=True),
    }
    if settings.DEBUG:
        logger.debug(message)

    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_password_expiration_reminder_mail(user):
    subject = _('Security notice')
    recipient_list = [user.email]
    message = _("""
    Hello %(name)s:
    </br>
    Your password will expire in %(date_password_expired)s,
    </br>
    For your account security, please click on the link below to update your password in time
    </br>
    <a href="%(update_password_url)s">Click here update password</a>
    </br>
    If your password has expired, please click 
    <a href="%(forget_password_url)s?email=%(email)s">Password expired</a> 
    to apply for a password reset email.

    </br>
    ---

    </br>
    <a href="%(login_url)s">Login direct</a>

    </br>
    """) % {
        'name': user.name,
        'date_password_expired': datetime.fromtimestamp(datetime.timestamp(
            user.date_password_expired)).strftime('%Y-%m-%d %H:%M'),
        'update_password_url': reverse('users:user-password-update', external=True),
        'forget_password_url': reverse('users:forgot-password', external=True),
        'email': user.email,
        'login_url': reverse('authentication:login', external=True),
    }
    if settings.DEBUG:
        logger.debug(message)

    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_reset_ssh_key_mail(user):
    subject = _('SSH Key Reset')
    recipient_list = [user.email]
    message = _("""
    Hello %(name)s:
    </br>
    Your ssh public key has been reset by site administrator.
    Please login and reset your ssh public key.
    </br>
    <a href="%(login_url)s">Login direct</a>

    </br>
    """) % {
        'name': user.name,
        'login_url': reverse('authentication:login', external=True),
    }
    if settings.DEBUG:
        logger.debug(message)

    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def check_user_valid(**kwargs):
    password = kwargs.pop('password', None)
    public_key = kwargs.pop('public_key', None)
    email = kwargs.pop('email', None)
    username = kwargs.pop('username', None)

    if username:
        user = get_object_or_none(User, username=username)
    elif email:
        user = get_object_or_none(User, email=email)
    else:
        user = None

    if user is None:
        return None, _('User not exist')
    elif not user.is_valid:
        return None, _('Disabled or expired')

    if password and authenticate(username=username, password=password):
        return user, ''

    if public_key and user.public_key:
        public_key_saved = user.public_key.split()
        if len(public_key_saved) == 1:
            if public_key == public_key_saved[0]:
                return user, ''
        elif len(public_key_saved) > 1:
            if public_key == public_key_saved[1]:
                return user, ''
    return None, _('Password or SSH public key invalid')


def get_user_or_tmp_user(request):
    user = request.user
    tmp_user = get_tmp_user_from_cache(request)
    if user.is_authenticated:
        return user
    elif tmp_user:
        return tmp_user
    else:
        raise Http404("Not found this user")


def get_tmp_user_from_cache(request):
    if not request.session.session_key:
        return None
    user = cache.get(request.session.session_key+'user')
    return user


def set_tmp_user_to_cache(request, user):
    cache.set(request.session.session_key+'user', user, 600)


def redirect_user_first_login_or_index(request, redirect_field_name):
    if request.user.is_first_login:
        return reverse('users:user-first-login')
    return request.POST.get(
        redirect_field_name,
        request.GET.get(redirect_field_name, reverse('index')))


def generate_otp_uri(request, issuer="Jumpserver"):
    user = get_user_or_tmp_user(request)
    otp_secret_key = cache.get(request.session.session_key+'otp_key', '')
    if not otp_secret_key:
        otp_secret_key = base64.b32encode(os.urandom(10)).decode('utf-8')
    cache.set(request.session.session_key+'otp_key', otp_secret_key, 600)
    totp = pyotp.TOTP(otp_secret_key)
    otp_issuer_name = settings.OTP_ISSUER_NAME or issuer
    return totp.provisioning_uri(name=user.username, issuer_name=otp_issuer_name), otp_secret_key


def check_otp_code(otp_secret_key, otp_code):
    if not otp_secret_key or not otp_code:
        return False
    totp = pyotp.TOTP(otp_secret_key)
    otp_valid_window = settings.OTP_VALID_WINDOW or 0
    return totp.verify(otp=otp_code, valid_window=otp_valid_window)


def get_password_check_rules():
    check_rules = []
    for rule in settings.SECURITY_PASSWORD_RULES:
        key = "id_{}".format(rule.lower())
        value = getattr(settings, rule)
        if not value:
            continue
        check_rules.append({'key': key, 'value': int(value)})
    return check_rules


def check_password_rules(password):
    pattern = r"^"
    if settings.SECURITY_PASSWORD_UPPER_CASE:
        pattern += '(?=.*[A-Z])'
    if settings.SECURITY_PASSWORD_LOWER_CASE:
        pattern += '(?=.*[a-z])'
    if settings.SECURITY_PASSWORD_NUMBER:
        pattern += '(?=.*\d)'
    if settings.SECURITY_PASSWORD_SPECIAL_CHAR:
        pattern += '(?=.*[`~!@#\$%\^&\*\(\)-=_\+\[\]\{\}\|;:\'\",\.<>\/\?])'
    pattern += '[a-zA-Z\d`~!@#\$%\^&\*\(\)-=_\+\[\]\{\}\|;:\'\",\.<>\/\?]'
    pattern += '.{' + str(settings.SECURITY_PASSWORD_MIN_LENGTH-1) + ',}$'
    match_obj = re.match(pattern, password)
    return bool(match_obj)


key_prefix_limit = "_LOGIN_LIMIT_{}_{}"
key_prefix_block = "_LOGIN_BLOCK_{}"


# def increase_login_failed_count(key_limit, key_block):
def increase_login_failed_count(username, ip):
    key_limit = key_prefix_limit.format(username, ip)
    count = cache.get(key_limit)
    count = count + 1 if count else 1

    limit_time = settings.SECURITY_LOGIN_LIMIT_TIME
    cache.set(key_limit, count, int(limit_time)*60)


def clean_failed_count(username, ip):
    key_limit = key_prefix_limit.format(username, ip)
    key_block = key_prefix_block.format(username)
    cache.delete(key_limit)
    cache.delete(key_block)


def is_block_login(username, ip):
    key_limit = key_prefix_limit.format(username, ip)
    key_block = key_prefix_block.format(username)
    count = cache.get(key_limit, 0)

    limit_count = settings.SECURITY_LOGIN_LIMIT_COUNT
    limit_time = settings.SECURITY_LOGIN_LIMIT_TIME

    if count >= limit_count:
        cache.set(key_block, 1, int(limit_time)*60)
    if count and count >= limit_count:
        return True


def is_need_unblock(key_block):
    if not cache.get(key_block):
        return False
    return True


def construct_user_email(username, email):
    if '@' not in email:
        if '@' in username:
            email = username
        else:
            email = '{}@{}'.format(username, settings.EMAIL_SUFFIX)
    return email

