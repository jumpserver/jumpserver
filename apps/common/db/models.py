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
from functools import partial

from django.db.models import *
from django.db import router, transaction
from django.db.models.signals import m2m_changed
from django.db.models.functions import Concat
from django.utils.translation import ugettext_lazy as _
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.db.models.fields.related import ManyToManyField

from common.const.signals import POST_ADD, PRE_ADD


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


def bulk_create_relations(
        model, related_model, m2m_field_name, objs, related_pks,
        batch_size=None, ignore_conflicts=False
):
    """
    本函数相当于：
    ```
        for obj in objs:
            obj.m2m_field_name.add(*related_pks)
    ```
    但不会每个 obj 都执行一条数据库插入
    """

    # 类型声明
    m2m_desc: ManyToManyDescriptor
    m2m_field: ManyToManyField

    m2m_desc = getattr(model, m2m_field_name)
    reverse = m2m_desc.reverse
    m2m_field = m2m_desc.field
    through = m2m_desc.through
    db = router.db_for_write(through, instance=objs[0])

    if not reverse:
        model_attname = m2m_field.m2m_column_name()
        to_add_attname = m2m_field.m2m_reverse_name()
    else:
        to_add_attname = m2m_field.m2m_column_name()
        model_attname = m2m_field.m2m_reverse_name()

    sender = partial(
        m2m_changed.send,
        sender=through,
        reverse=reverse,
        model=related_model,
        pk_set=related_pks,
        using=db
    )

    to_create = []
    for obj in objs:
        for to_add_pk in related_pks:
            data = {model_attname: obj.pk, to_add_attname: to_add_pk}
            to_create.append(through(**data))

    with transaction.atomic(using=db, savepoint=False):
        [sender(instance=obj, action=PRE_ADD) for obj in objs]
        through.objects.bulk_create(
            to_create, batch_size=batch_size, ignore_conflicts=ignore_conflicts
        )
        [sender(instance=obj, action=POST_ADD) for obj in objs]
