from itertools import islice

from django.db import models
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from common.const import ConfirmOrIgnore
from common.db.models import JMSBaseModel
from orgs.mixins.models import JMSOrgBaseModel
from .base import AccountBaseAutomation
from ...const import AutomationTypes

__all__ = ['CheckAccountAutomation', 'AccountRisk', 'RiskChoice', 'CheckAccountEngine']


class CheckAccountAutomation(AccountBaseAutomation):
    engines = models.ManyToManyField('CheckAccountEngine', related_name='check_automations', verbose_name=_('Engines'))

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'engines': [engine.slug for engine in self.engines.all()],
        })
        return attr_json

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.check_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('account check automation')
        permissions = [
            ('view_checkaccountexecution', _('Can view check account execution')),
            ('add_checkaccountexecution', _('Can add check account execution')),
        ]


class RiskChoice(TextChoices):
    # 依赖自动发现的
    zombie = 'zombie', _('Long time no login')  # 好久没登录的账号, 禁用、删除
    ghost = 'ghost', _('Not managed')  # 未被纳管的账号, 纳管, 删除, 禁用
    group_changed = 'groups_changed', _('Groups change')  # 组变更, 确认
    sudo_changed = 'sudoers_changed', _('Sudo changed')  # sudo 变更, 确认
    authorized_keys_changed = 'authorized_keys_changed', _('Authorized keys changed')  # authorized_keys 变更, 确认
    account_deleted = 'account_deleted', _('Account delete')  # 账号被删除, 确认
    password_expired = 'password_expired', _('Password expired')  # 密码过期, 修改密码
    long_time_password = 'long_time_password', _('Long time no change')  # 好久没改密码的账号, 改密码

    weak_password = 'weak_password', _('Weak password')  # 弱密码, 改密
    password_error = 'password_error', _('Password error')  # 密码错误, 修改账号
    no_admin_account = 'no_admin_account', _('No admin account')  # 无管理员账号, 设置账号
    others = 'others', _('Others')  # 其他风险, 确认


class AccountRisk(JMSOrgBaseModel):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, related_name='risks', verbose_name=_('Asset'))
    username = models.CharField(max_length=32, verbose_name=_('Username'))
    risk = models.CharField(max_length=128, verbose_name=_('Risk'), choices=RiskChoice.choices)
    status = models.CharField(max_length=32, choices=ConfirmOrIgnore.choices, default='', blank=True, verbose_name=_('Status'))
    details = models.JSONField(default=list,  verbose_name=_('Details'))

    class Meta:
        verbose_name = _('Account risk')
        unique_together = ('asset', 'username', 'risk')

    def __str__(self):
        return f"{self.username}@{self.asset} - {self.risk}"

    @classmethod
    def gen_fake_data(cls, count=1000, batch_size=50):
        from assets.models import Asset
        from accounts.models import Account

        assets = Asset.objects.all()
        accounts = Account.objects.all()

        counter = iter(range(count))
        while True:
            batch = list(islice(counter, batch_size))
            if not batch:
                break

            to_create = []
            for i in batch:
                asset = assets[i % len(assets)]
                account = accounts[i % len(accounts)]
                risk = RiskChoice.choices[i % len(RiskChoice.choices)][0]
                to_create.append(cls(asset=asset, username=account.username, risk=risk))

            cls.objects.bulk_create(to_create)


class CheckAccountEngine(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    slug = models.SlugField(max_length=128, verbose_name=_('Slug'), unique=True) #
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    def __str__(self):
        return self.name

    def internals(self):
        return [
            'check_gathered_account',
            'check_account_secret'
        ]

