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
from functools import reduce, partial
import inspect

from django.db.models import *
from django.db.models import QuerySet
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


class UnionQuerySet(QuerySet):
    after_union = ['order_by']
    not_return_qs = [
        'query', 'get', 'create', 'get_or_create',
        'update_or_create', 'bulk_create', 'count',
        'latest', 'earliest', 'first', 'last', 'aggregate',
        'exists', 'update', 'delete', 'as_manager', 'explain',
    ]

    def __init__(self, *queryset_list):
        self.queryset_list = queryset_list
        self.after_union_items = []
        self.before_union_items = []

    def __execute(self):
        queryset_list = []
        for qs in self.queryset_list:
            for attr, args, kwargs in self.before_union_items:
                qs = getattr(qs, attr)(*args, **kwargs)
            queryset_list.append(qs)
        union_qs = reduce(lambda x, y: x.union(y), queryset_list)
        for attr, args, kwargs in self.after_union_items:
            union_qs = getattr(union_qs, attr)(*args, **kwargs)
        return union_qs

    def __before_union_perform(self, item, *args, **kwargs):
        self.before_union_items.append((item, args, kwargs))
        return self.__clone(*self.queryset_list)

    def __after_union_perform(self, item, *args, **kwargs):
        self.after_union_items.append((item, args, kwargs))
        return self.__clone(*self.queryset_list)

    def __clone(self, *queryset_list):
        uqs = UnionQuerySet(*queryset_list)
        uqs.after_union_items = self.after_union_items
        uqs.before_union_items = self.before_union_items
        return uqs

    def __getattribute__(self, item):
        if item.startswith('__') or item in UnionQuerySet.__dict__ or item in [
            'queryset_list', 'after_union_items', 'before_union_items'
        ]:
            return object.__getattribute__(self, item)

        if item in UnionQuerySet.not_return_qs:
            return getattr(self.__execute(), item)

        origin_item = object.__getattribute__(self, 'queryset_list')[0]
        origin_attr = getattr(origin_item, item, None)
        if not inspect.ismethod(origin_attr):
            return getattr(self.__execute(), item)

        if item in UnionQuerySet.after_union:
            attr = partial(self.__after_union_perform, item)
        else:
            attr = partial(self.__before_union_perform, item)
        return attr

    def __getitem__(self, item):
        return self.__execute()[item]

    def __iter__(self):
        return iter(self.__execute())

    def __str__(self):
        return str(self.__execute())

    def __repr__(self):
        return repr(self.__execute())

    @classmethod
    def test_it(cls):
        from assets.models import Asset
        assets1 = Asset.objects.filter(hostname__startswith='a')
        assets2 = Asset.objects.filter(hostname__startswith='b')

        qs = cls(assets1, assets2)
        return qs
