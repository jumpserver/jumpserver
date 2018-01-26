# ~*~ coding: utf-8 ~*~
#
from __future__ import unicode_literals
import base64
import logging
import uuid

import requests
import ipaddress
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth import authenticate, login as auth_login
from django.utils.translation import ugettext as _
from django.core.cache import cache

from common.tasks import send_mail_async
from common.utils import reverse, get_object_or_none
from .models import User, LoginLog


logger = logging.getLogger('jumpserver')


class AdminUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        elif not self.request.user.is_superuser:
            self.raise_exception = True
            return False
        return True


def send_user_created_mail(user):
    subject = _('Create account successfully')
    recipient_list = [user.email]
    message = _("""
    Hello %(name)s:
    </br>
    Your account has been created successfully
    </br>
    <a href="%(rest_password_url)s?token=%(rest_password_token)s">click here to set your password</a>
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
        'login_url': reverse('users:login', external=True),
    }
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
        'login_url': reverse('users:login', external=True),
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
        'login_url': reverse('users:login', external=True),
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


def refresh_token(token, user, expiration=settings.TOKEN_EXPIRATION or 3600):
    cache.set(token, user.id, expiration)


def generate_token(request, user):
    expiration = settings.TOKEN_EXPIRATION or 3600
    remote_addr = request.META.get('REMOTE_ADDR', '')
    if not isinstance(remote_addr, bytes):
        remote_addr = remote_addr.encode("utf-8")
    remote_addr = base64.b16encode(remote_addr) #.replace(b'=', '')
    token = cache.get('%s_%s' % (user.id, remote_addr))
    if not token:
        token = uuid.uuid4().hex
        cache.set(token, user.id, expiration)
        cache.set('%s_%s' % (user.id, remote_addr), token, expiration)
    return token


def validate_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        pass
    return False


def write_login_log(username, type='', ip='', user_agent=''):
    if not (ip and validate_ip(ip)):
        ip = ip[:15]
        city = "Unknown"
    else:
        city = get_ip_city(ip)
    LoginLog.objects.create(
        username=username, type=type,
        ip=ip, city=city, user_agent=user_agent
    )


def get_ip_city(ip, timeout=10):
    # Taobao ip api: http://ip.taobao.com//service/getIpInfo.php?ip=8.8.8.8
    # Sina ip api: http://int.dpool.sina.com.cn/iplookup/iplookup.php?ip=8.8.8.8&format=json

    url = 'http://int.dpool.sina.com.cn/iplookup/iplookup.php?ip=%s&format=json' % ip
    try:
        r = requests.get(url, timeout=timeout)
    except requests.Timeout:
        r = None
    city = 'Unknown'
    if r and r.status_code == 200:
        try:
            data = r.json()
            if not isinstance(data, int) and data['ret'] == 1:
                city = data['country'] + ' ' + data['city']
        except ValueError:
            pass
    return city
