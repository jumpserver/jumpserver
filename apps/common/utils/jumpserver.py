from django.core.cache import cache
from django.shortcuts import reverse

from .random import random_string


__all__ = ['FlashMessageUtil']


class FlashMessageUtil:
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
