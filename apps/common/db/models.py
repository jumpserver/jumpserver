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

from django.db import models
from django.db import transaction
from django.db.models import F, ExpressionWrapper, CASCADE
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from ..const.signals import SKIP_SIGNAL


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
