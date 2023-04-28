# -*- coding: utf-8 -*-
#
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
    def get_response(redirect_url, title, msg, m_type='message'):
        message_data = {'title': title, 'interval': 5, 'redirect_url': redirect_url, m_type: msg}
        return FlashMessageUtil.gen_and_redirect_to(message_data)

    def get_success_response(self, redirect_url, title, msg):
        return self.get_response(redirect_url, title, msg)

    def get_failed_response(self, redirect_url, title, msg):
        return self.get_response(redirect_url, title, msg, 'error')
