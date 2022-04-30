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
    domain_enabled = models.BooleanField(default=True, verbose_name=_("Domain enabled"))
    domain_default = models.ForeignKey(
        'assets.Domain', null=True, on_delete=models.SET_NULL,
        verbose_name=_("Domain default")
    )
    protocols_enabled = models.BooleanField(default=True, verbose_name=_("Protocols enabled"))
    protocols_default = models.CharField(
        max_length=128, default='', blank=True, verbose_name=_("Protocols default")
    )
    admin_user_enabled = models.BooleanField(default=True, verbose_name=_("Admin user enabled"))
    admin_user_default = models.ForeignKey(
        'assets.SystemUser', null=True, on_delete=models.SET_NULL,
        verbose_name=_("Admin user default")
    )

    def get_type_meta(self):
        meta = Category.platform_meta().get(self.category, {})
        types = dict(AllTypes.category_types())[self.category]
        type_meta = types.platform_meta().get(self.type, {})
        meta.update(type_meta)
        return meta

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

