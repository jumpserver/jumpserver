from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import AllTypes
from assets.const import Protocol
from common.db.fields import JsonDictTextField

__all__ = ['Platform', 'PlatformProtocol', 'PlatformAutomation']


class PlatformProtocol(models.Model):
    SETTING_ATTRS = {
        'console': True,
        'security': 'any,tls,rdp',
        'sftp_enabled': True,
        'sftp_home': '/tmp'
    }
    default = models.BooleanField(default=False, verbose_name=_('Default'))
    required = models.BooleanField(default=False, verbose_name=_('Required'))
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    port = models.IntegerField(verbose_name=_('Port'))
    setting = models.JSONField(verbose_name=_('Setting'), default=dict)
    platform = models.ForeignKey('Platform', on_delete=models.CASCADE, related_name='protocols')

    def __str__(self):
        return '{}/{}'.format(self.name, self.port)

    @property
    def primary(self):
        primary_protocol_name = AllTypes.get_primary_protocol_name(
            self.platform.category, self.platform.type
        )
        return self.name == primary_protocol_name

    @property
    def secret_types(self):
        return Protocol.settings().get(self.name, {}).get('secret_types')


class PlatformAutomation(models.Model):
    ansible_enabled = models.BooleanField(default=False, verbose_name=_("Enabled"))
    ansible_config = models.JSONField(default=dict, verbose_name=_("Ansible config"))
    ping_enabled = models.BooleanField(default=False, verbose_name=_("Ping enabled"))
    ping_method = models.CharField(max_length=32, blank=True, null=True, verbose_name=_("Ping method"))
    gather_facts_enabled = models.BooleanField(default=False, verbose_name=_("Gather facts enabled"))
    gather_facts_method = models.TextField(max_length=32, blank=True, null=True, verbose_name=_("Gather facts method"))
    push_account_enabled = models.BooleanField(default=False, verbose_name=_("Push account enabled"))
    push_account_method = models.TextField(max_length=32, blank=True, null=True, verbose_name=_("Push account method"))
    change_secret_enabled = models.BooleanField(default=False, verbose_name=_("Change password enabled"))
    change_secret_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Change password method"))
    verify_account_enabled = models.BooleanField(default=False, verbose_name=_("Verify account enabled"))
    verify_account_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Verify account method"))
    gather_accounts_enabled = models.BooleanField(default=False, verbose_name=_("Gather facts enabled"))
    gather_accounts_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Gather facts method")
    )


class Platform(models.Model):
    """
    对资产提供 约束和默认值
    对资产进行抽象
    """

    class CharsetChoices(models.TextChoices):
        utf8 = 'utf8', 'UTF-8'
        gbk = 'gbk', 'GBK'

    name = models.SlugField(verbose_name=_("Name"), unique=True, allow_unicode=True)
    category = models.CharField(default='host', max_length=32, verbose_name=_("Category"))
    type = models.CharField(max_length=32, default='linux', verbose_name=_("Type"))
    meta = JsonDictTextField(blank=True, null=True, verbose_name=_("Meta"))
    internal = models.BooleanField(default=False, verbose_name=_("Internal"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("Comment"))
    # 资产有关的
    charset = models.CharField(
        default=CharsetChoices.utf8, choices=CharsetChoices.choices, max_length=8, verbose_name=_("Charset")
    )
    domain_enabled = models.BooleanField(default=True, verbose_name=_("Domain enabled"))
    protocols_enabled = models.BooleanField(default=True, verbose_name=_("Protocols enabled"))
    # 账号有关的
    su_enabled = models.BooleanField(default=False, verbose_name=_("Su enabled"))
    su_method = models.CharField(max_length=32, blank=True, null=True, verbose_name=_("Su method"))
    automation = models.OneToOneField(PlatformAutomation, on_delete=models.CASCADE, related_name='platform',
                                      blank=True, null=True, verbose_name=_("Automation"))

    @property
    def type_constraints(self):
        return AllTypes.get_constraints(self.category, self.type)

    @classmethod
    def default(cls):
        linux, created = cls.objects.get_or_create(
            defaults={'name': 'Linux'}, name='Linux'
        )
        return linux.id

    @property
    def primary_protocol(self):
        primary_protocol_name = AllTypes.get_primary_protocol_name(self.category, self.type)
        return self.protocols.filter(name=primary_protocol_name).first()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Platform")
        # ordering = ('name',)
