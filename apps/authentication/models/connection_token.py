import time
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from orgs.mixins.models import OrgModelMixin

from django.db import models
from common.utils import lazyproperty
from common.utils.timezone import as_current_tz
from common.db.models import JMSBaseModel


def date_expired_default():
    return timezone.now() + timedelta(seconds=settings.CONNECTION_TOKEN_EXPIRATION)


class ConnectionToken(OrgModelMixin, JMSBaseModel):
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,  null=True, blank=True,
        related_name='connection_tokens', verbose_name=_('User')
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='connection_tokens', verbose_name=_('Asset'),
    )
    user_display = models.CharField(max_length=128, default='', verbose_name=_("User display"))
    asset_display = models.CharField(max_length=128, default='', verbose_name=_("Asset display"))
    protocol = ''
    account = models.CharField(max_length=128, default='', verbose_name=_("Account"))
    secret = models.CharField(max_length=64, default='', verbose_name=_("Secret"))
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_("Date expired"))

    class Meta:
        ordering = ('-date_expired',)
        verbose_name = _('Connection token')
        permissions = [
            ('view_connectiontokensecret', _('Can view connection token secret'))
        ]

    @property
    def is_expired(self):
        return self.date_expired < timezone.now()

    @property
    def expire_time(self):
        interval = self.date_expired - timezone.now()
        seconds = interval.total_seconds()
        if seconds < 0:
            seconds = 0
        return int(seconds)

    @property
    def is_valid(self):
        return not self.is_expired

    @classmethod
    def get_default_date_expired(cls):
        return date_expired_default()

    def expire(self):
        self.date_expired = timezone.now()
        self.save()

    def renewal(self):
        """ 续期 Token，将来支持用户自定义创建 token 后，续期策略要修改 """
        self.date_expired = self.get_default_date_expired()
        self.save()

    # actions 和 expired_at 在 check_valid() 中赋值
    actions = expire_at = None

    def check_valid(self):
        from perms.utils.account import PermAccountUtil
        if self.is_expired:
            is_valid = False
            error = _('Connection token expired at: {}').format(as_current_tz(self.date_expired))
            return is_valid, error
        if not self.user:
            is_valid = False
            error = _('User not exists')
            return is_valid, error
        if not self.user.is_valid:
            is_valid = False
            error = _('User invalid, disabled or expired')
            return is_valid, error
        if not self.asset:
            is_valid = False
            error = _('Asset not exists')
            return is_valid, error
        if not self.asset.is_active:
            is_valid = False
            error = _('Asset inactive')
            return is_valid, error
        if not self.account:
            is_valid = False
            error = _('Account not exists')
            return is_valid, error

        actions, expire_at = PermAccountUtil().validate_permission(
            self.user, self.asset, self.account
        )
        if not actions or expire_at < time.time():
            is_valid = False
            error = _('User has no permission to access asset or permission expired')
            return is_valid, error
        self.actions = actions
        self.expire_at = expire_at
        return True, ''

    @lazyproperty
    def domain(self):
        domain = self.asset.domain if self.asset else None
        return domain

    @lazyproperty
    def gateway(self):
        from assets.models import Domain
        if not self.domain:
            return
        self.domain: Domain
        return self.domain.random_gateway()

    @lazyproperty
    def cmd_filter_rules(self):
        from assets.models import CommandFilterRule
        kwargs = {
            'user_id': self.user.id,
            'account': self.account,
        }
        if self.asset:
            kwargs['asset_id'] = self.asset.id
        rules = CommandFilterRule.get_queryset(**kwargs)
        return rules


class SuperConnectionToken(ConnectionToken):
    class Meta:
        proxy = True
        verbose_name = _("Super connection token")
