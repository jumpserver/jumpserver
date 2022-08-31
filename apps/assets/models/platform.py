from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import Category, AllTypes
from common.db.fields import JsonDictTextField


__all__ = ['Platform', 'PlatformProtocol']


class PlatformProtocol(models.Model):
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    port = models.IntegerField(verbose_name=_('Port'))
    setting = models.JSONField(verbose_name=_('Setting'), default=dict)


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
    category = models.CharField(default='host', max_length=32, verbose_name=_("Category"))
    type = models.CharField(max_length=32, default='linux', verbose_name=_("Type"))
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
    protocols = models.ManyToManyField(PlatformProtocol, blank=True, verbose_name=_("Protocols"))
    # Accounts
    # 这应该和账号有关
    su_enabled = models.BooleanField(default=False, verbose_name=_("Su enabled"))
    su_method = models.CharField(max_length=32, blank=True, null=True, verbose_name=_("SU method"))
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

    @staticmethod
    def set_default_platforms_ops(platform_model):
        default_ok = {
            'su_enabled': True,
            'su_method': 'sudo',
            'domain_enabled': True,
            'change_password_enabled': True,
            'change_password_method': 'change_password_linux',
            'verify_account_enabled': True,
            'verify_account_method': 'ansible_posix_ping',
        }
        db_default = {
            'su_enabled': False,
            'domain_enabled': True,
            'change_password_enabled': True,
            'verify_account_enabled': True,
        }

        platform_ops_map = {
            ('host', 'linux'): {
                **default_ok,
                'change_password_method': 'change_password_linux',
                'verify_account_method': 'ansible_posix_ping'
            },
            ('host', 'windows'): {
                **default_ok,
                'su_enabled': False,
                'change_password_method': 'change_password_windows',
                'verify_account_method': 'ansible_win_ping'
            },
            ('host', 'unix'): {
                **default_ok,
                'verify_account_method': 'ansible_posix_ping',
                'change_password_method': 'change_password_aix'
            },
            ('database', 'mysql'): {
                **db_default,
                'verify_account_method': 'mysql_ping',
                'change_password_method': 'change_password_mysql'
            },
            ('database', 'postgresql'): {
                **db_default,
                'verify_account_method': 'postgresql_ping',
                'change_password_method': 'change_password_postgresql'
            },
            ('database', 'oracle'): {
                **db_default,
                'verify_account_method': 'oracle_ping',
                'change_password_method': 'change_password_oracle'
            },
            ('database', 'sqlserver'): {
                **db_default,
                'verify_account_method': 'mysql_ping',
                'change_password_method': 'change_password_sqlserver'
            },
        }
        platforms = platform_model.objects.all()

        updated = []
        for p in platforms:
            attrs = platform_ops_map.get((p.category, p.type), {})
            if not attrs:
                continue
            for k, v in attrs.items():
                setattr(p, k, v)
            updated.append(p)
        platform_model.objects.bulk_update(updated, list(default_ok.keys()))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Platform")
        # ordering = ('name',)

