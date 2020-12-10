# -*- coding: utf-8 -*-
#
import json
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text

from ..utils import signer, crypto


__all__ = [
    'JsonMixin', 'JsonDictMixin', 'JsonListMixin', 'JsonTypeMixin',
    'JsonCharField', 'JsonTextField', 'JsonListCharField', 'JsonListTextField',
    'JsonDictCharField', 'JsonDictTextField', 'EncryptCharField',
    'EncryptTextField', 'EncryptMixin', 'EncryptJsonDictTextField',
    'EncryptJsonDictCharField',
]


class JsonMixin:
    tp = None

    @staticmethod
    def json_decode(data):
        try:
            return json.loads(data)
        except (TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def json_encode(data):
        return json.dumps(data)

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return value
        return self.json_decode(value)

    def to_python(self, value):
        if value is None:
            return value

        if not isinstance(value, str) or not value.startswith('"'):
            return value
        else:
            return self.json_decode(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.json_encode(value)


class JsonTypeMixin(JsonMixin):
    tp = dict

    def from_db_value(self, value, expression, connection, context=None):
        value = super().from_db_value(value, expression, connection, context)
        if not isinstance(value, self.tp):
            value = self.tp()
        return value

    def to_python(self, value):
        data = super().to_python(value)
        if not isinstance(data, self.tp):
            data = self.tp()
        return data

    def get_prep_value(self, value):
        if not isinstance(value, self.tp):
            value = self.tp()
        return self.json_encode(value)


class JsonDictMixin(JsonTypeMixin):
    tp = dict


class JsonDictCharField(JsonDictMixin, models.CharField):
    description = _("Marshal dict data to char field")


class JsonDictTextField(JsonDictMixin, models.TextField):
    description = _("Marshal dict data to text field")


class JsonListMixin(JsonTypeMixin):
    tp = list


class JsonStrListMixin(JsonListMixin):
    pass


class JsonListCharField(JsonListMixin, models.CharField):
    description = _("Marshal list data to char field")


class JsonListTextField(JsonListMixin, models.TextField):
    description = _("Marshal list data to text field")


class JsonCharField(JsonMixin, models.CharField):
    description = _("Marshal data to char field")


class JsonTextField(JsonMixin, models.TextField):
    description = _("Marshal data to text field")


class EncryptMixin:
    """
    EncryptMixin要放在最前面
    """

    def decrypt_from_signer(self, value):
        return signer.unsign(value) or ''

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return value
        value = force_text(value)

        plain_value = crypto.decrypt(value)

        # 如果没有解开，使用原来的signer解密
        if not plain_value:
            plain_value = self.decrypt_from_signer(value)

        # 可能和Json mix，所以要先解密，再json
        sp = super()
        if hasattr(sp, 'from_db_value'):
            plain_value = sp.from_db_value(plain_value, expression, connection, context)
        return plain_value

    def get_prep_value(self, value):
        if value is None:
            return value

        # 先 json 再解密
        sp = super()
        if hasattr(sp, 'get_prep_value'):
            value = sp.get_prep_value(value)
        value = force_text(value)
        # 替换新的加密方式
        return crypto.encrypt(value)


class EncryptTextField(EncryptMixin, models.TextField):
    description = _("Encrypt field using Secret Key")


class EncryptCharField(EncryptMixin, models.CharField):
    @staticmethod
    def change_max_length(kwargs):
        kwargs.setdefault('max_length', 1024)
        max_length = kwargs.get('max_length')
        if max_length < 129:
            max_length = 128
        max_length = max_length * 2
        kwargs['max_length'] = max_length

    def __init__(self, *args, **kwargs):
        self.change_max_length(kwargs)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        max_length = kwargs.pop('max_length')
        if max_length > 255:
            max_length = max_length // 2
        kwargs['max_length'] = max_length
        return name, path, args, kwargs


class EncryptJsonDictTextField(EncryptMixin, JsonDictTextField):
    pass


class EncryptJsonDictCharField(EncryptMixin, JsonDictCharField):
    pass

