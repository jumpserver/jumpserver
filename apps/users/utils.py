# ~*~ coding: utf-8 ~*~
#
from __future__ import unicode_literals
import os
import re
import pyotp
import base64
import logging
import uuid

import requests
import ipaddress
from django.http import Http404
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth import authenticate
from django.utils.translation import ugettext as _
from django.core.cache import cache

from common.tasks import send_mail_async
from common.utils import reverse, get_object_or_none
from common.models import common_settings, Setting
from common.forms import SecuritySettingForm
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
    Username: %(username)s
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
        'username': user.username,
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
    remote_addr = base64.b16encode(remote_addr)  # .replace(b'=', '')
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


def write_login_log(*args, **kwargs):
    ip = kwargs.get('ip', '')
    if not (ip and validate_ip(ip)):
        ip = ip[:15]
        city = "Unknown"
    else:
        city = get_ip_city(ip)
    kwargs.update({'ip': ip, 'city': city})
    LoginLog.objects.create(**kwargs)


def get_ip_city(ip, timeout=10):
    # Taobao ip api: http://ip.taobao.com/service/getIpInfo.php?ip=8.8.8.8
    # Sina ip api: http://int.dpool.sina.com.cn/iplookup/iplookup.php?ip=8.8.8.8&format=json

    url = 'http://ip.taobao.com/service/getIpInfo.php?ip=%s' % ip
    try:
        r = requests.get(url, timeout=timeout)
    except:
        r = None
    city = 'Unknown'
    if r and r.status_code == 200:
        try:
            data = r.json()
            if not isinstance(data, int) and data['code'] == 0:
                country = data['data']['country']
                _city = data['data']['city']
                if country == 'XX':
                    city = _city
                else:
                    city = ' '.join([country, _city])
        except ValueError:
            pass
    return city


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
    return totp.provisioning_uri(name=user.username, issuer_name=issuer), otp_secret_key


def check_otp_code(otp_secret_key, otp_code):
    if not otp_secret_key or not otp_code:
        return False
    totp = pyotp.TOTP(otp_secret_key)
    return totp.verify(otp_code)


def get_password_check_rules():
    check_rules = []
    min_length = settings.DEFAULT_PASSWORD_MIN_LENGTH
    min_name = 'SECURITY_PASSWORD_MIN_LENGTH'
    base_filed = SecuritySettingForm.base_fields
    password_setting = Setting.objects.filter(name__startswith='SECURITY_PASSWORD')

    if not password_setting:
        # 用户还没有设置过密码校验规则
        label = base_filed.get(min_name).label
        label += ' ' + str(min_length) + _('Bit')
        id = 'rule_' + min_name
        rules = {'id': id, 'label': label}
        check_rules.append(rules)

    for setting in password_setting:
        if setting.cleaned_value:
            id = 'rule_' + setting.name
            label = base_filed.get(setting.name).label
            if setting.name == min_name:
                label += str(setting.cleaned_value) + _('Bit')
                min_length = setting.cleaned_value
            rules = {'id': id, 'label': label}
            check_rules.append(rules)

    return check_rules, min_length


def check_password_rules(password):
    min_field_name = 'SECURITY_PASSWORD_MIN_LENGTH'
    upper_field_name = 'SECURITY_PASSWORD_UPPER_CASE'
    lower_field_name = 'SECURITY_PASSWORD_LOWER_CASE'
    number_field_name = 'SECURITY_PASSWORD_NUMBER'
    special_field_name = 'SECURITY_PASSWORD_SPECIAL_CHAR'
    min_length = getattr(common_settings, min_field_name) or \
                 settings.DEFAULT_PASSWORD_MIN_LENGTH

    password_setting = Setting.objects.filter(name__startswith='SECURITY_PASSWORD')
    if not password_setting:
        pattern = r"^.{" + str(min_length) + ",}$"
    else:
        pattern = r"^"
        for setting in password_setting:
            if setting.cleaned_value and setting.name == upper_field_name:
                pattern += '(?=.*[A-Z])'
            elif setting.cleaned_value and setting.name == lower_field_name:
                pattern += '(?=.*[a-z])'
            elif setting.cleaned_value and setting.name == number_field_name:
                pattern += '(?=.*\d)'
            elif setting.cleaned_value and setting.name == special_field_name:
                pattern += '(?=.*[`~!@#\$%\^&\*\(\)-=_\+\[\]\{\}\|;:\'",\.<>\/\?])'
        pattern += '[a-zA-Z\d`~!@#\$%\^&\*\(\)-=_\+\[\]\{\}\|;:\'",\.<>\/\?]'

    match_obj = re.match(pattern, password)
    return bool(match_obj)


key_prefix_limit = "_LOGIN_LIMIT_{}_{}"
key_prefix_block = "_LOGIN_BLOCK_{}"


# def increase_login_failed_count(key_limit, key_block):
def increase_login_failed_count(username, ip):
    key_limit = key_prefix_limit.format(username, ip)
    count = cache.get(key_limit)
    count = count + 1 if count else 1

    limit_time = common_settings.SECURITY_LOGIN_LIMIT_TIME or \
        settings.DEFAULT_LOGIN_LIMIT_TIME
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

    limit_count = common_settings.SECURITY_LOGIN_LIMIT_COUNT or \
        settings.DEFAULT_LOGIN_LIMIT_COUNT
    limit_time = common_settings.SECURITY_LOGIN_LIMIT_TIME or \
        settings.DEFAULT_LOGIN_LIMIT_TIME

    if count >= limit_count:
        cache.set(key_block, 1, int(limit_time)*60)
    if count and count >= limit_count:
        return True


def is_need_unblock(key_block):
    if not cache.get(key_block):
        return False
    return True
