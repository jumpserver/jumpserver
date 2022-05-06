# -*- coding: utf-8 -*-
#

import logging
from rest_framework import serializers
from django.conf import settings

from common.utils import rsa_decrypt
from jumpserver.utils import current_request

__all__ = [
    'ReadableHiddenField', 'EncryptedField'
]


# ReadableHiddenField
# -------------------


class ReadableHiddenField(serializers.HiddenField):
    """ 可读的 HiddenField """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.write_only = False

    def to_representation(self, value):
        if hasattr(value, 'id'):
            return getattr(value, 'id')
        return value


class EncryptedField(serializers.CharField):
    def to_internal_value(self, value):
        value = super().to_internal_value(value)
        private_key_name = settings.SESSION_RSA_PRIVATE_KEY_NAME
        private_key = current_request.session.get(private_key_name)
        if not private_key:
            return value

        try:
            value= rsa_decrypt(value, private_key)
        except Exception as e:
            logging.error('Decrypt field error: {}'.format(e))
        return value
