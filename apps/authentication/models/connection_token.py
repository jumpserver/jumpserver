from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import PermissionDenied

from assets.const import Protocol
from common.db.fields import EncryptCharField
from common.db.models import JMSBaseModel
from common.utils import lazyproperty, pretty_string
from common.utils.timezone import as_current_tz
from orgs.mixins.models import OrgModelMixin


def date_expired_default():
    return timezone.now() + timedelta(seconds=settings.CONNECTION_TOKEN_EXPIRATION)


class ConnectionToken(OrgModelMixin, JMSBaseModel):
    value = models.CharField(max_length=64, default='', verbose_name=_("Value"))
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='connection_tokens', verbose_name=_('User')
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='connection_tokens', verbose_name=_('Asset'),
    )
    account_name = models.CharField(max_length=128, verbose_name=_("Account name"))  # 登录账号Name
    input_username = models.CharField(max_length=128, default='', blank=True, verbose_name=_("Input Username"))
    input_secret = EncryptCharField(max_length=64, default='', blank=True, verbose_name=_("Input Secret"))
    protocol = models.CharField(
        choices=Protocol.choices, max_length=16, default=Protocol.ssh, verbose_name=_("Protocol")
    )
    connect_method = models.CharField(max_length=32, verbose_name=_("Connect method"))
    user_display = models.CharField(max_length=128, default='', verbose_name=_("User display"))
    asset_display = models.CharField(max_length=128, default='', verbose_name=_("Asset display"))
    date_expired = models.DateTimeField(
        default=date_expired_default, verbose_name=_("Date expired")
    )

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

    def save(self, *args, **kwargs):
        self.asset_display = pretty_string(self.asset, max_length=128)
        self.user_display = pretty_string(self.user, max_length=128)
        return super().save(*args, **kwargs)

    def expire(self):
        self.date_expired = timezone.now()
        self.save()

    def renewal(self):
        """ 续期 Token，将来支持用户自定义创建 token 后，续期策略要修改 """
        self.date_expired = date_expired_default()
        self.save()

    @lazyproperty
    def permed_account(self):
        from perms.utils import PermAccountUtil
        permed_account = PermAccountUtil().validate_permission(
            self.user, self.asset, self.account_name
        )
        return permed_account

    @lazyproperty
    def actions(self):
        return self.permed_account.actions

    @lazyproperty
    def expire_at(self):
        return self.permed_account.date_expired.timestamp()

    def is_valid(self):
        if self.is_expired:
            error = _('Connection token expired at: {}').format(as_current_tz(self.date_expired))
            raise PermissionDenied(error)
        if not self.user or not self.user.is_valid:
            error = _('No user or invalid user')
            raise PermissionDenied(error)
        if not self.asset or not self.asset.is_active:
            is_valid = False
            error = _('No asset or inactive asset')
            return is_valid, error
        if not self.account_name:
            error = _('No account')
            raise PermissionDenied(error)

        if not self.permed_account or not self.permed_account.actions:
            msg = 'user `{}` not has asset `{}` permission for login `{}`'.format(
                self.user, self.asset, self.account_name
            )
            raise PermissionDenied(msg)

        if self.permed_account.date_expired < timezone.now():
            raise PermissionDenied('Expired')
        return True

    @lazyproperty
    def platform(self):
        return self.asset.platform

    @lazyproperty
    def account(self):
        if not self.asset:
            return None

        account = self.asset.accounts.filter(name=self.account_name).first()
        if self.account_name == '@INPUT' or not account:
            return {
                'name': self.account_name,
                'username': self.username,
                'secret_type': 'password',
                'secret': self.secret
            }
        else:
            return {
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': account.secret or self.secret
            }

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
