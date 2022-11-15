# -*- coding: utf-8 -*-
#
import six
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import ChoiceField

from common.db.fields import BitChoices
from common.utils import decrypt_password

__all__ = [
    "ReadableHiddenField",
    "EncryptedField",
    "LabeledChoiceField",
    "ObjectRelatedField",
    "BitChoicesField",
    "TreeChoicesMixin"
]


# ReadableHiddenField
# -------------------


class ReadableHiddenField(serializers.HiddenField):
    """可读的 HiddenField"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.write_only = False

    def to_representation(self, value):
        if hasattr(value, "id"):
            return getattr(value, "id")
        return value


class EncryptedField(serializers.CharField):
    def __init__(self, write_only=None, **kwargs):
        if write_only is None:
            write_only = True
        kwargs["write_only"] = write_only
        super().__init__(**kwargs)

    def to_internal_value(self, value):
        value = super().to_internal_value(value)
        return decrypt_password(value)


class LabeledChoiceField(ChoiceField):
    def __init__(self, *args, **kwargs):
        super(LabeledChoiceField, self).__init__(*args, **kwargs)
        self.choice_mapper = {
            six.text_type(key): value for key, value in self.choices.items()
        }

    def to_representation(self, value):
        if value is None:
            return value
        return {
            "value": value,
            "label": self.choice_mapper.get(six.text_type(value), value),
        }

    def to_internal_value(self, data):
        if isinstance(data, dict):
            return data.get("value")
        return super(LabeledChoiceField, self).to_internal_value(data)


class ObjectRelatedField(serializers.RelatedField):
    default_error_messages = {
        "required": _("This field is required."),
        "does_not_exist": _('Invalid pk "{pk_value}" - object does not exist.'),
        "incorrect_type": _("Incorrect type. Expected pk value, received {data_type}."),
    }

    def __init__(self, **kwargs):
        self.attrs = kwargs.pop("attrs", None) or ("id", "name")
        self.many = kwargs.get("many", False)
        super().__init__(**kwargs)

    def to_representation(self, value):
        data = {}
        for attr in self.attrs:
            data[attr] = getattr(value, attr)
        return data

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            pk = data
        else:
            pk = data.get("id") or data.get("pk") or data.get(self.attrs[0])
        queryset = self.get_queryset()
        try:
            if isinstance(data, bool):
                raise TypeError
            return queryset.get(pk=pk)
        except ObjectDoesNotExist:
            self.fail("does_not_exist", pk_value=pk)
        except (TypeError, ValueError):
            self.fail("incorrect_type", data_type=type(pk).__name__)


class TreeChoicesMixin:
    tree = []


class BitChoicesField(TreeChoicesMixin, serializers.MultipleChoiceField):
    """
    位字段
    """

    def __init__(self, choice_cls, **kwargs):
        assert issubclass(choice_cls, BitChoices)
        choices = [(c.name, c.label) for c in choice_cls]
        self.tree = choice_cls.tree()
        self._choice_cls = choice_cls
        super().__init__(choices=choices, **kwargs)

    def to_representation(self, value):
        if isinstance(value, list) and len(value) == 1:
            # Swagger 会使用 field.choices.keys() 迭代传递进来
            return [
                {"value": c.name, "label": c.label}
                for c in self._choice_cls
                if c.name == value[0]
            ]
        return [
            {"value": c.name, "label": c.label}
            for c in self._choice_cls
            if c.value & value == c.value
        ]

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError(_("Invalid data type, should be list"))
        value = 0
        if not data:
            return value
        if isinstance(data[0], dict):
            data = [d["value"] for d in data]
        # 所有的
        if "all" in data:
            for c in self._choice_cls:
                value |= c.value
            return value

        name_value_map = {c.name: c.value for c in self._choice_cls}
        for name in data:
            if name not in name_value_map:
                raise serializers.ValidationError(_("Invalid choice: {}").format(name))
            value |= name_value_map[name]
        return value
