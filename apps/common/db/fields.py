# -*- coding: utf-8 -*-
#
import json

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from rest_framework.utils.encoders import JSONEncoder

from common.local import add_encrypted_field_set
from common.utils import signer, crypto
from .validators import PortRangeValidator

__all__ = [
    "JsonMixin",
    "JsonDictMixin",
    "JsonListMixin",
    "JsonTypeMixin",
    "JsonCharField",
    "JsonTextField",
    "JsonListCharField",
    "JsonListTextField",
    "JsonDictCharField",
    "JsonDictTextField",
    "EncryptCharField",
    "EncryptTextField",
    "EncryptMixin",
    "EncryptJsonDictTextField",
    "EncryptJsonDictCharField",
    "PortField",
    "PortRangeField",
    "BitChoices",
    "TreeChoices",
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
        return json.dumps(data, cls=JSONEncoder)

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
        return signer.unsign(value) or ""

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
        if hasattr(sp, "from_db_value"):
            plain_value = sp.from_db_value(plain_value, expression, connection, context)
        return plain_value

    def get_prep_value(self, value):
        if value is None:
            return value

        # 先 json 再解密
        sp = super()
        if hasattr(sp, "get_prep_value"):
            value = sp.get_prep_value(value)
        value = force_text(value)
        # 替换新的加密方式
        return crypto.encrypt(value)


class EncryptTextField(EncryptMixin, models.TextField):
    description = _("Encrypt field using Secret Key")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class EncryptCharField(EncryptMixin, models.CharField):
    @staticmethod
    def change_max_length(kwargs):
        kwargs.setdefault("max_length", 1024)
        max_length = kwargs.get("max_length")
        if max_length < 129:
            max_length = 128
        max_length = max_length * 2
        kwargs["max_length"] = max_length

    def __init__(self, *args, **kwargs):
        self.change_max_length(kwargs)
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        max_length = kwargs.pop("max_length")
        if max_length > 255:
            max_length = max_length // 2
        kwargs["max_length"] = max_length
        return name, path, args, kwargs


class EncryptJsonDictTextField(EncryptMixin, JsonDictTextField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class EncryptJsonDictCharField(EncryptMixin, JsonDictCharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class PortField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "blank": False,
                "null": False,
                "validators": [MinValueValidator(0), MaxValueValidator(65535)],
            }
        )
        super().__init__(*args, **kwargs)


class TreeChoices(models.Choices):
    @classmethod
    def is_tree(cls):
        return True

    @classmethod
    def branches(cls):
        return [i for i in cls]

    @classmethod
    def tree(cls):
        if not cls.is_tree():
            return []
        root = [_("All"), cls.branches()]
        return [cls.render_node(root)]

    @classmethod
    def render_node(cls, node):
        if isinstance(node, models.Choices):
            return {
                "value": node.name,
                "label": node.label,
            }
        else:
            name, children = node
            return {
                "value": name,
                "label": name,
                "children": [cls.render_node(child) for child in children],
            }

    @classmethod
    def all(cls):
        return [i[0] for i in cls.choices]


class BitChoices(models.IntegerChoices, TreeChoices):
    @classmethod
    def is_tree(cls):
        return False

    @classmethod
    def all(cls):
        value = 0
        for c in cls:
            value |= c.value
        return value


class PortRangeField(models.CharField):
    def __init__(self, **kwargs):
        kwargs['max_length'] = 16
        super().__init__(**kwargs)
        self.validators.append(PortRangeValidator())
