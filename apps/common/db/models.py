"""
此文件作为 `django.db.models` 的 shortcut

这样做的优点与缺点为：
优点：
    - 包命名都统一为 `models`
    - 用户在使用的时候只导入本文件即可
缺点：
    - 此文件中添加代码的时候，注意不要跟 `django.db.models` 中的命名冲突
"""

import uuid

from django.db.models import *
from django.db.models.functions import Concat
from django.utils.translation import ugettext_lazy as _


class Choice(str):
    def __new__(cls, value, label=''):  # `deepcopy` 的时候不会传 `label`
        self = super().__new__(cls, value)
        self.label = label
        return self


class ChoiceSetType(type):
    def __new__(cls, name, bases, attrs):
        _choices = []
        collected = set()
        new_attrs = {}
        for k, v in attrs.items():
            if isinstance(v, tuple):
                v = Choice(*v)
                assert v not in collected, 'Cannot be defined repeatedly'
                _choices.append(v)
                collected.add(v)
            new_attrs[k] = v
        for base in bases:
            if hasattr(base, '_choices'):
                for c in base._choices:
                    if c not in collected:
                        _choices.append(c)
                        collected.add(c)
        new_attrs['_choices'] = _choices
        new_attrs['_choices_dict'] = {c: c.label for c in _choices}
        return type.__new__(cls, name, bases, new_attrs)

    def __contains__(self, item):
        return self._choices_dict.__contains__(item)

    def __getitem__(self, item):
        return self._choices_dict.__getitem__(item)

    def get(self, item, default=None):
        return self._choices_dict.get(item, default)

    @property
    def choices(self):
        return [(c, c.label) for c in self._choices]


class ChoiceSet(metaclass=ChoiceSetType):
    choices = None  # 用于 Django Model 中的 choices 配置， 为了代码提示在此声明


class JMSBaseModel(Model):
    created_by = CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    updated_by = CharField(max_length=32, null=True, blank=True, verbose_name=_('Updated by'))
    date_created = DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    date_updated = DateTimeField(auto_now=True, verbose_name=_('Date updated'))

    class Meta:
        abstract = True


class JMSModel(JMSBaseModel):
    id = UUIDField(default=uuid.uuid4, primary_key=True)

    class Meta:
        abstract = True


def concated_display(name1, name2):
    return Concat(F(name1), Value('('), F(name2), Value(')'))


def output_as_string(field_name):
    return ExpressionWrapper(F(field_name), output_field=CharField())
