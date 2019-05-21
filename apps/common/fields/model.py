# -*- coding: utf-8 -*-
#
import json
from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..utils import get_signer


__all__ = [
    'JsonMixin', 'JsonDictMixin', 'JsonListMixin', 'JsonTypeMixin',
    'JsonCharField', 'JsonTextField', 'JsonListCharField', 'JsonListTextField',
    'JsonDictCharField', 'JsonDictTextField', 'EncryptCharField',
    'EncryptTextField', 'EncryptMixin', 'EncryptJsonDictTextField',
]
signer = get_signer()


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

    def from_db_value(self, value, expression, connection, context):
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

    def from_db_value(self, value, expression, connection, context):
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
    def from_db_value(self, value, expression, connection, context):
        if value is not None:
            return signer.unsign(value)
        return None

    def get_prep_value(self, value):
        if value is None:
            return value
        return signer.sign(value)


class EncryptTextField(EncryptMixin, models.TextField):
    description = _("Encrypt field using Secret Key")


class EncryptCharField(EncryptMixin, models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 2048
        super().__init__(*args, **kwargs)


class EncryptJsonDictTextField(EncryptMixin, JsonDictTextField):
    pass


