# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from common.utils import FlashMessageUtil


class METAMixin:
    def get_next_url_from_meta(self):
        request_meta = self.request.META or {}
        next_url = None
        referer = request_meta.get('HTTP_REFERER', '')
        next_url_item = referer.rsplit('next=', 1)
        if len(next_url_item) > 1:
            next_url = next_url_item[-1]
        return next_url


class FlashMessageMixin:
    @staticmethod
    def get_response(redirect_url='', title='', msg='', m_type='message', interval=5):
        message_data = {
            'title': title, 'interval': interval,
            'redirect_url': redirect_url,
        }
        if m_type == 'error':
            message_data['error'] = msg
        else:
            message_data['message'] = msg
        return FlashMessageUtil.gen_and_redirect_to(message_data)

    def get_success_response(self, redirect_url, title, msg, **kwargs):
        return self.get_response(redirect_url, title, msg, m_type='success', **kwargs)

    def get_failed_response(self, redirect_url, title, msg, interval=10):
        return self.get_response(redirect_url, title, msg, 'error', interval)

    def get_verify_state_failed_response(self, redirect_uri):
        msg = _(
            "For your safety, automatic redirection login is not supported on the client."
            " If you need to open it in the client, please log in again")
        return self.get_failed_response(redirect_uri, msg, msg)

    def verify_state_with_session_key(self, session_key):
        return self.request.GET.get('state') == self.request.session.get(session_key)
