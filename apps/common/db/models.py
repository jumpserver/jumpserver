"""
此文件作为 `django.db.models` 的 shortcut

这样做的优点与缺点为：
优点：
    - 包命名都统一为 `models`
    - 用户在使用的时候只导入本文件即可
缺点：
    - 此文件中添加代码的时候，注意不要跟 `django.db.models` 中的命名冲突
"""

import inspect
import uuid
from functools import reduce, partial

from django.db import models
from django.db import transaction
from django.db.models import F, ExpressionWrapper, CASCADE
from django.db.models import QuerySet
from django.utils.translation import ugettext_lazy as _

from ..const.signals import SKIP_SIGNAL


class BitOperationChoice:
    NONE = 0
    NAME_MAP: dict
    DB_CHOICES: tuple
    NAME_MAP_REVERSE: dict

    @classmethod
    def value_to_choices(cls, value):
        if isinstance(value, list):
            return value
        value = int(value)
        choices = [cls.NAME_MAP[i] for i, j in cls.DB_CHOICES if value & i == i]
        return choices

    @classmethod
    def value_to_choices_display(cls, value):
        choices = cls.value_to_choices(value)
        return [str(dict(cls.choices())[i]) for i in choices]

    @classmethod
    def choices_to_value(cls, value):
        if not isinstance(value, list):
            return cls.NONE
        db_value = [
            cls.NAME_MAP_REVERSE[v] for v in value
            if v in cls.NAME_MAP_REVERSE.keys()
        ]
        if not db_value:
            return cls.NONE

        def to_choices(x, y):
            return x | y

        result = reduce(to_choices, db_value)
        return result

    @classmethod
    def choices(cls):
        return [(cls.NAME_MAP[i], j) for i, j in cls.DB_CHOICES]


class ChoicesMixin:
    _value2label_map_: dict

    @classmethod
    def get_label(cls, value: (str, int)):
        return cls._value2label_map_[value]


class BaseCreateUpdateModel(models.Model):
    created_by = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Created by'))
    updated_by = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Updated by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_('Date updated'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        abstract = True


class JMSBaseModel(BaseCreateUpdateModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.id)


def output_as_string(field_name):
    return ExpressionWrapper(F(field_name), output_field=models.CharField())


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


class MultiTableChildQueryset(QuerySet):

    def bulk_create(self, objs, batch_size=None):
        assert batch_size is None or batch_size > 0
        if not objs:
            return objs

        self._for_write = True
        objs = list(objs)
        parent_model = self.model._meta.pk.related_model

        parent_objs = []
        for obj in objs:
            parent_values = {}
            for field in [f for f in parent_model._meta.fields if hasattr(obj, f.name)]:
                parent_values[field.name] = getattr(obj, field.name)
            parent_objs.append(parent_model(**parent_values))
            setattr(obj, self.model._meta.pk.attname, obj.id)
        parent_model.objects.bulk_create(parent_objs, batch_size=batch_size)

        with transaction.atomic(using=self.db, savepoint=False):
            self._batched_insert(objs, self.model._meta.local_fields, batch_size)

        return objs


def CASCADE_SIGNAL_SKIP(collector, field, sub_objs, using):
    # 级联删除时，操作日志标记不保存，以免用户混淆
    try:
        for obj in sub_objs:
            setattr(obj, SKIP_SIGNAL, True)
    except:
        pass

    CASCADE(collector, field, sub_objs, using)
