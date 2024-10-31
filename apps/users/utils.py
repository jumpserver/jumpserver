# ~*~ coding: utf-8 ~*~
#
import base64
import json
import logging
import os
import re
import time

import pyotp
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _

from common.tasks import send_mail_async
from common.utils import reverse, get_object_or_none, ip, safe_next_url, FlashMessageUtil
from .models import User

logger = logging.getLogger('jumpserver.users')


def send_user_created_mail(user):
    from .notifications import UserCreatedMsg

    recipient_list = [user.email]
    msg = UserCreatedMsg(user).html_msg
    subject = msg['subject']
    message = msg['message']

    if settings.DEBUG:
        try:
            print(message)
        except OSError:
            pass

    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def get_user_or_pre_auth_user(request):
    user = request.user
    if user.is_authenticated:
        return user
    pre_auth_user_id = request.session.get('user_id')
    user = None
    if pre_auth_user_id:
        user = get_object_or_none(User, pk=pre_auth_user_id)
    return user


def get_redirect_client_url(request):
    bearer_token, date_expired = request.user.create_bearer_token(request, age=3600*36*5)
    data = {
        'type': 'auth',
        'bearer_token': bearer_token,
        'date_expired': date_expired.timestamp()
    }
    buf = base64.b64encode(json.dumps(data).encode()).decode()
    redirect_url = 'jms://{}'.format(buf)
    message_data = {
        'title': _('Auth success'),
        'message': _("Redirecting to JumpServer Client"),
        'redirect_url': redirect_url,
        'interval': 1,
        'has_cancel': False,
    }
    url = FlashMessageUtil.gen_message_url(message_data)
    return url


def redirect_user_first_login_or_index(request, redirect_field_name):
    url = request.POST.get(redirect_field_name)
    if not url:
        url = request.GET.get(redirect_field_name)

    if url == 'client':
        url = get_redirect_client_url(request)

    url = safe_next_url(url, request=request)
    # 防止 next 地址为 None
    if not url or url.lower() in ['none']:
        url = reverse('index')
    return url


def generate_otp_uri(username, otp_secret_key=None, issuer="JumpServer"):
    if otp_secret_key is None:
        otp_secret_key = base64.b32encode(os.urandom(10)).decode('utf-8')
    totp = pyotp.TOTP(otp_secret_key)
    otp_issuer_name = settings.OTP_ISSUER_NAME or issuer
    uri = totp.provisioning_uri(name=username, issuer_name=otp_issuer_name)
    return uri, otp_secret_key


def check_otp_code(otp_secret_key, otp_code):
    if not otp_secret_key or not otp_code:
        return False
    totp = pyotp.TOTP(otp_secret_key)
    otp_valid_window = settings.OTP_VALID_WINDOW or 0
    return totp.verify(otp=otp_code, valid_window=otp_valid_window)


def get_password_check_rules(user):
    check_rules = []
    for rule in settings.SECURITY_PASSWORD_RULES:
        key = "id_{}".format(rule.lower())
        if user.is_org_admin and rule == 'SECURITY_PASSWORD_MIN_LENGTH':
            rule = 'SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH'
        value = getattr(settings, rule)
        if not value:
            continue
        check_rules.append({'key': key, 'value': int(value)})
    return check_rules


def check_password_rules(password, is_org_admin=False):
    pattern = r"^"
    if settings.SECURITY_PASSWORD_UPPER_CASE:
        pattern += '(?=.*[A-Z])'
    if settings.SECURITY_PASSWORD_LOWER_CASE:
        pattern += '(?=.*[a-z])'
    if settings.SECURITY_PASSWORD_NUMBER:
        pattern += '(?=.*\d)'
    if settings.SECURITY_PASSWORD_SPECIAL_CHAR:
        pattern += '(?=.*[`~!@#$%^&*()\-=_+\[\]{}|;:\'",.<>/?])'
    pattern += '[a-zA-Z\d`~!@#\$%\^&\*\(\)-=_\+\[\]\{\}\|;:\'\",\.<>\/\?]'
    if is_org_admin:
        min_length = settings.SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH
    else:
        min_length = settings.SECURITY_PASSWORD_MIN_LENGTH
    pattern += '.{' + str(min_length - 1) + ',}$'
    match_obj = re.match(pattern, password)
    return bool(match_obj)


class BlockUtil:
    BLOCK_KEY_TMPL: str

    def __init__(self, username):
        username = username.lower()
        self.block_key = self.BLOCK_KEY_TMPL.format(username)
        self.key_ttl = int(settings.SECURITY_LOGIN_LIMIT_TIME) * 60

    def block(self):
        cache.set(self.block_key, True, self.key_ttl)

    def is_block(self):
        return bool(cache.get(self.block_key))


class BlockUtilBase:
    LIMIT_KEY_TMPL: str
    BLOCK_KEY_TMPL: str

    def __init__(self, username, ip):
        username = username.lower()
        self.username = username
        self.ip = ip
        self.limit_key = self.LIMIT_KEY_TMPL.format(username, ip)
        self.block_key = self.BLOCK_KEY_TMPL.format(username)
        self.key_ttl = int(settings.SECURITY_LOGIN_LIMIT_TIME) * 60

    def get_remainder_times(self):
        times_up = settings.SECURITY_LOGIN_LIMIT_COUNT
        times_failed = self.get_failed_count()
        times_remainder = int(times_up) - int(times_failed)
        return times_remainder

    def incr_failed_count(self) -> int:
        limit_key = self.limit_key
        count = cache.get(limit_key, 0)
        count += 1
        cache.set(limit_key, count, self.key_ttl)

        limit_count = settings.SECURITY_LOGIN_LIMIT_COUNT
        if count >= limit_count:
            cache.set(self.block_key, True, self.key_ttl)
        return limit_count - count

    def get_failed_count(self):
        count = cache.get(self.limit_key, 0)
        return count

    def clean_failed_count(self):
        cache.delete(self.limit_key)
        cache.delete(self.block_key)

    @classmethod
    def unblock_user(cls, username):
        username = username.lower()
        key_limit = cls.LIMIT_KEY_TMPL.format(username, '*')
        key_block = cls.BLOCK_KEY_TMPL.format(username)
        # Redis 尽量不要用通配
        cache.delete_pattern(key_limit)
        cache.delete(key_block)

    @classmethod
    def is_user_block(cls, username):
        username = username.lower()
        block_key = cls.BLOCK_KEY_TMPL.format(username)
        return bool(cache.get(block_key))

    def is_block(self):
        return bool(cache.get(self.block_key))


class BlockGlobalIpUtilBase:
    LIMIT_KEY_TMPL: str
    BLOCK_KEY_TMPL: str

    def __init__(self, ip):
        self.ip = ip
        self.limit_key = self.LIMIT_KEY_TMPL.format(ip)
        self.block_key = self.BLOCK_KEY_TMPL.format(ip)
        self.key_ttl = int(settings.SECURITY_LOGIN_IP_LIMIT_TIME) * 60

    @property
    def ip_in_black_list(self):
        return ip.contains_ip(self.ip, settings.SECURITY_LOGIN_IP_BLACK_LIST)

    @property
    def ip_in_white_list(self):
        return ip.contains_ip(self.ip, settings.SECURITY_LOGIN_IP_WHITE_LIST)

    def set_block_if_need(self):
        if self.ip_in_white_list or self.ip_in_black_list:
            return
        count = cache.get(self.limit_key, 0)
        count += 1
        cache.set(self.limit_key, count, self.key_ttl)

        limit_count = settings.SECURITY_LOGIN_IP_LIMIT_COUNT
        if count < limit_count:
            return
        cache.set(self.block_key, True, self.key_ttl)

    def clean_block_if_need(self):
        cache.delete(self.limit_key)
        cache.delete(self.block_key)

    def is_block(self):
        if self.ip_in_white_list:
            return False
        if self.ip_in_black_list:
            return True
        return bool(cache.get(self.block_key))


class LoginBlockUtil(BlockUtilBase):
    LIMIT_KEY_TMPL = "_LOGIN_LIMIT_{}_{}"
    BLOCK_KEY_TMPL = "_LOGIN_BLOCK_{}"


class MFABlockUtils(BlockUtilBase):
    LIMIT_KEY_TMPL = "_MFA_LIMIT_{}_{}"
    BLOCK_KEY_TMPL = "_MFA_BLOCK_{}"


class LoginIpBlockUtil(BlockGlobalIpUtilBase):
    LIMIT_KEY_TMPL = "_LOGIN_LIMIT_{}"
    BLOCK_KEY_TMPL = "_LOGIN_BLOCK_IP_{}"


def validate_emails(emails):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    for e in emails:
        e = e or ''
        if re.match(pattern, e):
            return e


def construct_user_email(username, email, email_suffix=''):
    default = f'{username}@{email_suffix or settings.EMAIL_SUFFIX}'
    emails = [email, username]
    email = validate_emails(emails)
    return email or default


def flatten_dict(d, parent_key='', sep='.'):
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep=sep))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.update(flatten_dict(item, f"{new_key}[{i}]", sep=sep))
                else:
                    items[f"{new_key}[{i}]"] = item
        else:
            items[new_key] = v
    return items


def map_attributes(default_profile, profile, attributes):
    detail = default_profile
    for local_name, remote_name in attributes.items():
        value = profile.get(remote_name)
        if value:
            detail[local_name] = value
    return detail


def get_current_org_members():
    from orgs.utils import current_org
    return current_org.get_members()


def is_auth_time_valid(session, key):
    return True if session.get(key, 0) > time.time() else False


def is_auth_password_time_valid(session):
    return is_auth_time_valid(session, 'auth_password_expired_at')


def is_auth_otp_time_valid(session):
    return is_auth_time_valid(session, 'auth_otp_expired_at')


def is_confirm_time_valid(session, key):
    if not settings.SECURITY_VIEW_AUTH_NEED_MFA:
        return True
    mfa_verify_time = session.get(key, 0)
    if time.time() - mfa_verify_time < settings.SECURITY_MFA_VERIFY_TTL:
        return True
    return False


def is_auth_confirm_time_valid(session):
    return is_confirm_time_valid(session, 'MFA_VERIFY_TIME')
