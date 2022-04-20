from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import Category, AllTypes
from common.fields.model import JsonDictTextField


__all__ = ['Platform']


class Platform(models.Model):
    CHARSET_CHOICES = (
        ('utf8', 'UTF-8'),
        ('gbk', 'GBK'),
    )
    name = models.SlugField(verbose_name=_("Name"), unique=True, allow_unicode=True)
    category = models.CharField(max_length=16, choices=Category.choices, verbose_name=_("Category"))
    type = models.CharField(choices=AllTypes.choices, max_length=32, default='Linux', verbose_name=_("Type"))
    charset = models.CharField(default='utf8', choices=CHARSET_CHOICES, max_length=8, verbose_name=_("Charset"))
    meta = JsonDictTextField(blank=True, null=True, verbose_name=_("Meta"))
    internal = models.BooleanField(default=False, verbose_name=_("Internal"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("Comment"))

    @classmethod
    def default(cls):
        linux, created = cls.objects.get_or_create(
            defaults={'name': 'Linux'}, name='Linux'
        )
        return linux.id

    def is_windows(self):
        return self.type.lower() in ('windows',)

    def is_unixlike(self):
        return self.type.lower() in ("linux", "unix", "macos", "bsd")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Platform")
        # ordering = ('name',)

