# -*- coding: utf-8 -*-
#
import phonenumbers
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import ChoiceField, empty

from common.db.fields import TreeChoices, JSONManyToManyField as ModelJSONManyToManyField
from common.local import add_encrypted_field_set
from common.utils import decrypt_password

__all__ = [
    "ReadableHiddenField",
    "EncryptedField",
    "LabeledChoiceField",
    "ObjectRelatedField",
    "BitChoicesField",
    "TreeChoicesField",
    "LabeledMultipleChoiceField",
    "PhoneField",
    "JSONManyToManyField",
    "LabelRelatedField",
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
        encrypted_key = kwargs.pop('encrypted_key', None)
        super().__init__(**kwargs)
        add_encrypted_field_set(encrypted_key or self.label)

    def to_internal_value(self, value):
        value = super().to_internal_value(value)
        return decrypt_password(value)


class LabeledChoiceField(ChoiceField):
    def to_representation(self, key):
        if key is None:
            return key
        label = self.choices.get(key, key)
        return {"value": key, "label": label}

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.get("value")

        if isinstance(data, str) and "(" in data and data.endswith(")"):
            data = data.strip(")").split('(')[-1]
        return super(LabeledChoiceField, self).to_internal_value(data)


class LabeledMultipleChoiceField(serializers.MultipleChoiceField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.choice_mapper = {
            key: value for key, value in self.choices.items()
        }

    def to_representation(self, keys):
        if keys is None:
            return keys
        return [
            {"value": key, "label": self.choice_mapper.get(key)}
            for key in keys
        ]

    def to_internal_value(self, data):
        if not data:
            return data

        if isinstance(data[0], dict):
            return [item.get("value") for item in data]
        else:
            return data


class LabelRelatedField(serializers.RelatedField):
    def __init__(self, **kwargs):
        queryset = kwargs.pop("queryset", None)
        if queryset is None:
            from labels.models import LabeledResource
            queryset = LabeledResource.objects.all()

        kwargs = {**kwargs}
        read_only = kwargs.get("read_only", False)
        if not read_only:
            kwargs["queryset"] = queryset
        super().__init__(**kwargs)

    def to_representation(self, value):
        if value is None:
            return value
        return str(value.label)

    def to_internal_value(self, data):
        from labels.models import LabeledResource, Label
        if data is None:
            return data
        if isinstance(data, dict):
            pk = data.get("id") or data.get("pk")
            label = Label.objects.get(pk=pk)
        else:
            k, v = data.split(":", 1)
            label, __ = Label.objects.get_or_create(name=k, value=v, defaults={'name': k, 'value': v})
        return LabeledResource(label=label)


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
            if not hasattr(value, attr):
                continue
            data[attr] = getattr(value, attr)
        return data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, Model):
            return queryset.get(pk=data.pk)

        if not isinstance(data, dict):
            pk = data
        else:
            pk = data.get("id") or data.get("pk") or data.get(self.attrs[0])

        try:
            if isinstance(data, bool):
                raise TypeError
            return queryset.get(pk=pk)
        except ObjectDoesNotExist:
            self.fail("does_not_exist", pk_value=pk)
        except (TypeError, ValueError):
            self.fail("incorrect_type", data_type=type(pk).__name__)


class TreeChoicesField(serializers.MultipleChoiceField):
    def __init__(self, choice_cls, **kwargs):
        assert issubclass(choice_cls, TreeChoices)
        choices = [(c.name, c.label) for c in choice_cls]
        self.tree = choice_cls.tree()
        self._choice_cls = choice_cls
        super().__init__(choices=choices, **kwargs)

    def to_internal_value(self, data):
        if not data:
            return data
        if isinstance(data[0], dict):
            return [item.get("value") for item in data]
        else:
            return data


class BitChoicesField(TreeChoicesField):
    """
    位字段
    """

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

    def run_validation(self, data=empty):
        """
        备注:
        创建授权规则不包含 actions 字段时, 会使用默认值(AssetPermission 中设置),
        会直接使用 ['connect', '...'] 等字段保存到数据库，导致类型错误
        这里将获取到的值再执行一下 to_internal_value 方法, 转化为内部值
        """
        data = super().run_validation(data)
        if isinstance(data, int):
            return data
        value = self.to_internal_value(data)
        self.run_validators(value)
        return value


class PhoneField(serializers.CharField):

    def to_internal_value(self, data):
        if isinstance(data, dict):
            code = data.get('code')
            phone = data.get('phone', '')
            if code and phone:
                code = code.replace('+', '')
                data = '+{}{}'.format(code, phone)
            else:
                data = phone
        try:
            phone = phonenumbers.parse(data, 'CN')
            data = '+{}{}'.format(phone.country_code, phone.national_number)
        except phonenumbers.NumberParseException:
            data = '+86{}'.format(data)

        return super().to_internal_value(data)

    def to_representation(self, value):
        if value:
            try:
                phone = phonenumbers.parse(value, 'CN')
                value = {'code': '+%s' % phone.country_code, 'phone': phone.national_number}
            except phonenumbers.NumberParseException:
                value = {'code': '+86', 'phone': value}
        return value


class JSONManyToManyField(serializers.JSONField):
    def to_representation(self, manager):
        if manager is None:
            return manager
        value = manager.value
        if not isinstance(value, dict):
            return {"type": "ids", "ids": []}
        if value.get("type") == "ids":
            valid_ids = manager.all().values_list("id", flat=True)
            valid_ids = [str(i) for i in valid_ids]
            return {"type": "ids", "ids": valid_ids}
        return value

    def to_internal_value(self, data):
        if not data:
            data = {}
        try:
            ModelJSONManyToManyField.check_value(data)
        except ValueError as e:
            raise serializers.ValidationError(e)
        return super().to_internal_value(data)
