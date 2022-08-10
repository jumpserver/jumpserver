from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import Category, AllTypes
from common.db.fields import JsonDictTextField


__all__ = ['Platform']


class Platform(models.Model):
    """
    对资产提供 约束和默认值
    对资产进行抽象
    """
    CHARSET_CHOICES = (
        ('utf8', 'UTF-8'),
        ('gbk', 'GBK'),
    )
    name = models.SlugField(verbose_name=_("Name"), unique=True, allow_unicode=True)
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.HOST, verbose_name=_("Category"))
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
    protocols_default = models.JSONField(
        max_length=128, default=list, blank=True, verbose_name=_("Protocols default")
    )
    # Accounts
    # 这应该和账号有关
    su_enabled = models.BooleanField(default=False)
    su_method = models.TextField(max_length=32, blank=True, null=True, verbose_name=_("SU method"))
    ping_enabled = models.BooleanField(default=False)
    ping_method = models.TextField(max_length=32, blank=True, null=True, verbose_name=_("Ping method"))
    verify_account_enabled = models.BooleanField(default=False, verbose_name=_("Verify account enabled"))
    verify_account_method = models.TextField(max_length=32, blank=True, null=True, verbose_name=_("Verify account method"))
    create_account_enabled = models.BooleanField(default=False, verbose_name=_("Create account enabled"))
    create_account_method = models.TextField(max_length=32, blank=True, null=True, verbose_name=_("Create account method"))
    change_password_enabled = models.BooleanField(default=False, verbose_name=_("Change password enabled"))
    change_password_method = models.TextField(max_length=32, blank=True, null=True, verbose_name=_("Change password method"))

    @property
    def type_constraints(self):
        return AllTypes.get_constraints(self.category, self.type)

    @classmethod
    def default(cls):
        linux, created = cls.objects.get_or_create(
            defaults={'name': 'Linux'}, name='Linux'
        )
        return linux.id

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Platform")
        # ordering = ('name',)

