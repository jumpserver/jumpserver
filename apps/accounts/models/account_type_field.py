from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin

__all__ = ['Field']


class Field(CommonModelMixin, models.Model):
    """ 字段: 账号类型关联的其他附加字段, 用来动态构造创建/更新/查看账号所需的序列类 """
    class TypeChoices(models.TextChoices):
        int_field = 'int', 'Integer Field'
        char_field = 'char', 'Char Field'
        ip_field = 'ip', 'IPAddress Field'

    display_name = models.CharField(
        max_length=1024, verbose_name=_('Display name')
    )
    # 只能是字母、下划线的组合
    name = models.CharField(
        max_length=128, verbose_name=_('Name')
    )
    type = models.CharField(
        default=TypeChoices.char_field, choices=TypeChoices.choices, verbose_name=_('Type'),
    )
    initial = models.CharField(
        default=None, max_length=128, null=True, blank=True, verbose_name=_('Initial'),
    )
    required = models.BooleanField(
        default=None, null=True, blank=True, verbose_name=_('Required'),
    )
    default = models.CharField(
        default=None, max_length=128, null=True, blank=True, verbose_name=_('Default'),
    )
    read_only = models.BooleanField(
        default=False, verbose_name=_('Read only')
    )
    write_only = models.BooleanField(
        default=False, verbose_name=_('Write only'))
    allow_null = models.BooleanField(
        default=False, verbose_name=_('Allow null'))
    allow_blank = models.BooleanField(
        default=False, verbose_name=_('Allow blank'))
    max_length = models.IntegerField(
        default=None, null=True, verbose_name=_('Max length')
    )
    min_length = models.IntegerField(
        default=None, null=True, verbose_name=_('Min length')
    )
    max_value = models.IntegerField(
        default=None, null=True, verbose_name=_('Max value')
    )
    min_value = models.IntegerField(
        default=None, null=True, verbose_name=_('Min value')
    )
    label = models.CharField(
        default=None, null=True, blank=True, verbose_name=_('Label')
    )
    help_text = models.TextField(
        default=None, null=True, blank=True, verbose_name=_('Help text')
    )
    comment = models.TextField(
        default=None, null=True, blank=True, verbose_name=_('Comment')
    )

    def __str__(self):
        return '{} ({})'.format(self.display_name, self.name)