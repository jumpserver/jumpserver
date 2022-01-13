from django.core.cache import cache
from django.shortcuts import reverse, redirect
from django.utils.translation import gettext_noop

from .random import random_string


__all__ = ['FlashMessageUtil']


class FlashMessageUtil:
    """
    跳转到通用msg页面
    message_data: {
        'title': '',
        'message': '',
        'error': '',
        'redirect_url': '',
        'confirm_button': '',
        'cancel_url': ''
    }
    """
    @staticmethod
    def get_key(code):
        key = 'MESSAGE_{}'.format(code)
        return key

    @classmethod
    def get_message_code(cls, message_data):
        code = random_string(12)
        key = cls.get_key(code)
        cache.set(key, message_data, 60)
        return code

    @classmethod
    def get_message_by_code(cls, code):
        key = cls.get_key(code)
        return cache.get(key)

    @classmethod
    def gen_message_url(cls, message_data):
        code = cls.get_message_code(message_data)
        return reverse('common:flash-message') + f'?code={code}'

    @classmethod
    def gen_and_redirect_to(cls, message_data):
        url = cls.gen_message_url(message_data)
        return redirect(url)
