# -*- coding: utf-8 -*-
#
import time
from django.conf import settings

from common.utils import get_object_or_none, get_request_ip, get_logger
from users.models import User
from users.utils import (
    is_block_login, clean_failed_count, increase_login_failed_count
)
from . import errors
from .utils import check_user_valid
from .signals import post_auth_success, post_auth_failed

logger = get_logger(__name__)


class AuthMixin:
    request = None

    def get_user_from_session(self):
        if self.request.session.is_empty():
            raise errors.SessionEmptyError()
        if self.request.user and not self.request.user.is_anonymous:
            return self.request.user
        user_id = self.request.session.get('user_id')
        if not user_id:
            user = None
        else:
            user = get_object_or_none(User, pk=user_id)
        if not user:
            raise errors.SessionEmptyError()
        user.backend = self.request.session.get("auth_backend")
        return user

    def get_request_ip(self):
        ip = ''
        if hasattr(self.request, 'data'):
            ip = self.request.data.get('remote_addr', '')
        ip = ip or get_request_ip(self.request)
        return ip

    def check_is_block(self):
        if hasattr(self.request, 'data'):
            username = self.request.data.get("username")
        else:
            username = self.request.POST.get("username")
        ip = self.get_request_ip()
        if is_block_login(username, ip):
            logger.warn('Ip was blocked' + ': ' + username + ':' + ip)
            raise errors.BlockLoginError(username=username, ip=ip)

    def check_user_auth(self):
        self.check_is_block()
        request = self.request
        if hasattr(request, 'data'):
            username = request.data.get('username', '')
            password = request.data.get('password', '')
            public_key = request.data.get('public_key', '')
        else:
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
            public_key = request.POST.get('public_key', '')
        user, error = check_user_valid(
            username=username, password=password,
            public_key=public_key
        )
        ip = self.get_request_ip()
        if not user:
            raise errors.CredentialError(
                username=username, error=error, ip=ip, request=request
            )
        clean_failed_count(username, ip)
        request.session['auth_password'] = 1
        request.session['user_id'] = str(user.id)
        auth_backend = getattr(user, 'backend', 'django.contrib.auth.backends.ModelBackend')
        request.session['auth_backend'] = auth_backend
        return user

    def check_user_auth_if_need(self):
        request = self.request
        if request.session.get('auth_password') and \
                request.session.get('user_id'):
            user = self.get_user_from_session()
            if user:
                return user
        return self.check_user_auth()

    def check_user_mfa_if_need(self, user):
        if self.request.session.get('auth_mfa'):
            return
        if not user.mfa_enabled:
            return
        if not user.otp_secret_key and user.mfa_is_otp():
            return
        raise errors.MFARequiredError()

    def check_user_mfa(self, code):
        user = self.get_user_from_session()
        ok = user.check_mfa(code)
        if ok:
            self.request.session['auth_mfa'] = 1
            self.request.session['auth_mfa_time'] = time.time()
            self.request.session['auth_mfa_type'] = 'otp'
            return
        raise errors.MFAFailedError(username=user.username, request=self.request)

    def get_ticket(self):
        from tickets.models import Ticket
        ticket_id = self.request.session.get("auth_ticket_id")
        logger.debug('Login confirm ticket id: {}'.format(ticket_id))
        if not ticket_id:
            ticket = None
        else:
            ticket = get_object_or_none(Ticket, pk=ticket_id)
        return ticket

    def get_ticket_or_create(self, confirm_setting):
        ticket = self.get_ticket()
        if not ticket or ticket.status == ticket.STATUS_CLOSED:
            ticket = confirm_setting.create_confirm_ticket(self.request)
            self.request.session['auth_ticket_id'] = str(ticket.id)
        return ticket

    def check_user_login_confirm(self):
        ticket = self.get_ticket()
        if not ticket:
            raise errors.LoginConfirmOtherError('', "Not found")
        if ticket.status == ticket.STATUS_OPEN:
            raise errors.LoginConfirmWaitError(ticket.id)
        elif ticket.action == ticket.ACTION_APPROVE:
            self.request.session["auth_confirm"] = "1"
            return
        elif ticket.action == ticket.ACTION_REJECT:
            raise errors.LoginConfirmOtherError(
                ticket.id, ticket.get_action_display()
            )
        else:
            raise errors.LoginConfirmOtherError(
                ticket.id, ticket.get_status_display()
            )

    def check_user_login_confirm_if_need(self, user):
        if not settings.LOGIN_CONFIRM_ENABLE:
            return
        confirm_setting = user.get_login_confirm_setting()
        if self.request.session.get('auth_confirm') or not confirm_setting:
            return
        self.get_ticket_or_create(confirm_setting)
        self.check_user_login_confirm()

    def clear_auth_mark(self):
        self.request.session['auth_password'] = ''
        self.request.session['auth_user_id'] = ''
        self.request.session['auth_mfa'] = ''
        self.request.session['auth_confirm'] = ''
        self.request.session['auth_ticket_id'] = ''

    def send_auth_signal(self, success=True, user=None, username='', reason=''):
        if success:
            post_auth_success.send(
                sender=self.__class__, user=user, request=self.request
            )
        else:
            post_auth_failed.send(
                sender=self.__class__, username=username,
                request=self.request, reason=reason
            )
