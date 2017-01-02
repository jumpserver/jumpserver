# ~*~ coding: utf-8 ~*~
#
from __future__ import unicode_literals
import base64
import logging
import os
import re
import uuid

from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.core.cache import cache

from paramiko.rsakey import RSAKey

from common.tasks import send_mail_async
from common.utils import reverse, get_object_or_none
from .models import User


try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


logger = logging.getLogger('jumpserver')


class AdminUserRequiredMixin(UserPassesTestMixin):
    login_url = reverse_lazy('users:login')

    def test_func(self):
        return self.request.user.is_staff


def user_add_success_next(user):
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


# def validate_ssh_pk(text):
#     """
#     Expects a SSH private key as string.
#     Returns a boolean and a error message.
#     If the text is parsed as private key successfully,
#     (True,'') is returned. Otherwise,
#     (False, <message describing the error>) is returned.
#
#     from https://github.com/githubnemo/SSH-private-key-validator/blob/master/validate.py
#
#     """
#
#     if not text:
#         return False, 'No text given'
#
#     startPattern = re.compile("^-----BEGIN [A-Z]+ PRIVATE KEY-----")
#     optionPattern = re.compile("^.+: .+")
#     contentPattern = re.compile("^([a-zA-Z0-9+/]{64}|[a-zA-Z0-9+/]{1,64}[=]{0,2})$")
#     endPattern = re.compile("^-----END [A-Z]+ PRIVATE KEY-----")
#
#     def contentState(text):
#         for i in range(0, len(text)):
#             line = text[i]
#
#             if endPattern.match(line):
#                 if i == len(text) - 1 or len(text[i + 1]) == 0:
#                     return True, ''
#                 else:
#                     return False, 'At end but content coming'
#
#             elif not contentPattern.match(line):
#                 return False, 'Wrong string in content section'
#
#         return False, 'No content or missing end line'
#
#     def optionState(text):
#         for i in range(0, len(text)):
#             line = text[i]
#
#             if line[-1:] == '\\':
#                 return optionState(text[i + 2:])
#
#             if not optionPattern.match(line):
#                 return contentState(text[i + 1:])
#
#         return False, 'Expected option, found nothing'

    # def startState(text):
    #     if len(text) == 0 or not startPattern.match(text[0]):
    #         return False, 'Header is wrong'
    #     return optionState(text[1:])
    #
    # return startState([n.strip() for n in text.splitlines()])
#

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

    if password and user.password and user.check_password(password):
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


def refresh_token(token, user, expiration=3600):
    cache.set(token, user.id, expiration)


def generate_token(request, user):
    expiration = settings.CONFIG.TOKEN_EXPIRATION or 3600
    remote_addr = request.META.get('REMOTE_ADDR', '')
    remote_addr = base64.b16encode(remote_addr).replace('=', '')
    token = cache.get('%s_%s' % (user.id, remote_addr))
    if not token:
        token = uuid.uuid4().get_hex()
        print('Set cache: %s' % token)
        cache.set(token, user.id, expiration)
        cache.set('%s_%s' % (user.id, remote_addr), token, expiration)
    return token


