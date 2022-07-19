import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from rest_framework.authtoken.models import Token
from orgs.mixins.models import OrgModelMixin

from common.db import models
from common.utils import lazyproperty
from common.utils.timezone import as_current_tz


class AccessKey(models.Model):
    id = models.UUIDField(verbose_name='AccessKeyID', primary_key=True,
                          default=uuid.uuid4, editable=False)
    secret = models.UUIDField(verbose_name='AccessKeySecret',
                              default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='User',
                             on_delete=models.CASCADE, related_name='access_keys')
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_created = models.DateTimeField(auto_now_add=True)

    def get_id(self):
        return str(self.id)

    def get_secret(self):
        return str(self.secret)

    def get_full_value(self):
        return '{}:{}'.format(self.id, self.secret)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = _("Access key")


class PrivateToken(Token):
    """Inherit from auth token, otherwise migration is boring"""

    class Meta:
        verbose_name = _('Private Token')


class SSOToken(models.JMSBaseModel):
    """
    类似腾讯企业邮的 [单点登录](https://exmail.qq.com/qy_mng_logic/doc#10036)
    出于安全考虑，这里的 `token` 使用一次随即过期。但我们保留每一个生成过的 `token`。
    """
    authkey = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name=_('Token'))
    expired = models.BooleanField(default=False, verbose_name=_('Expired'))
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'), db_constraint=False)

    class Meta:
        verbose_name = _('SSO token')


def date_expired_default():
    return timezone.now() + timedelta(seconds=settings.CONNECTION_TOKEN_EXPIRATION)


class ConnectionToken(OrgModelMixin, models.JMSModel):
    class Type(models.TextChoices):
        asset = 'asset', _('Asset')
        application = 'application', _('Application')

    type = models.CharField(
        max_length=16, default=Type.asset, choices=Type.choices, verbose_name=_("Type")
    )
    secret = models.CharField(max_length=64, default='', verbose_name=_("Secret"))
    date_expired = models.DateTimeField(
        default=date_expired_default, verbose_name=_("Date expired")
    )

    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, verbose_name=_('User'),
        related_name='connection_tokens', null=True, blank=True
    )
    user_display = models.CharField(max_length=128, default='', verbose_name=_("User display"))
    system_user = models.ForeignKey(
        'assets.SystemUser', on_delete=models.SET_NULL, verbose_name=_('System user'),
        related_name='connection_tokens', null=True, blank=True
    )
    system_user_display = models.CharField(
        max_length=128, default='', verbose_name=_("System user display")
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL, verbose_name=_('Asset'),
        related_name='connection_tokens', null=True, blank=True
    )
    asset_display = models.CharField(max_length=128, default='', verbose_name=_("Asset display"))
    application = models.ForeignKey(
        'applications.Application', on_delete=models.SET_NULL, verbose_name=_('Application'),
        related_name='connection_tokens', null=True, blank=True
    )
    application_display = models.CharField(
        max_length=128, default='', verbose_name=_("Application display")
    )

    class Meta:
        ordering = ('-date_expired',)
        verbose_name = _('Connection token')
        permissions = [
            ('view_connectiontokensecret', _('Can view connection token secret'))
        ]

    @classmethod
    def get_default_date_expired(cls):
        return date_expired_default()

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

    def expire(self):
        self.date_expired = timezone.now()
        self.save()

    @property
    def is_valid(self):
        return not self.is_expired

    def is_type(self, tp):
        return self.type == tp

    def renewal(self):
        """ 续期 Token，将来支持用户自定义创建 token 后，续期策略要修改 """
        self.date_expired = self.get_default_date_expired()
        self.save()

    actions = expired_at = None  # actions 和 expired_at 在 check_valid() 中赋值

    def check_valid(self):
        from perms.utils.asset.permission import validate_permission as asset_validate_permission
        from perms.utils.application.permission import validate_permission as app_validate_permission

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

        if not self.system_user:
            is_valid = False
            error = _('System user not exists')
            return is_valid, error

        if self.is_type(self.Type.asset):
            if not self.asset:
                is_valid = False
                error = _('Asset not exists')
                return is_valid, error
            if not self.asset.is_active:
                is_valid = False
                error = _('Asset inactive')
                return is_valid, error
            has_perm, actions, expired_at = asset_validate_permission(
                self.user, self.asset, self.system_user
            )
            if not has_perm:
                is_valid = False
                error = _('User has no permission to access asset or permission expired')
                return is_valid, error
            self.actions = actions
            self.expired_at = expired_at

        elif self.is_type(self.Type.application):
            if not self.application:
                is_valid = False
                error = _('Application not exists')
                return is_valid, error
            has_perm, actions, expired_at = app_validate_permission(
                self.user, self.application, self.system_user
            )
            if not has_perm:
                is_valid = False
                error = _('User has no permission to access application or permission expired')
                return is_valid, error
            self.actions = actions
            self.expired_at = expired_at

        return True, ''

    @lazyproperty
    def domain(self):
        if self.asset:
            return self.asset.domain
        if not self.application:
            return
        if self.application.category_remote_app:
            asset = self.application.get_remote_app_asset()
            domain = asset.domain if asset else None
        else:
            domain = self.application.domain
        return domain

    @lazyproperty
    def gateway(self):
        from assets.models import Domain
        if not self.domain:
            return
        self.domain: Domain
        return self.domain.random_gateway()

    @lazyproperty
    def remote_app(self):
        if not self.application:
            return {}
        if not self.application.category_remote_app:
            return {}
        return self.application.get_rdp_remote_app_setting()

    @lazyproperty
    def asset_or_remote_app_asset(self):
        if self.asset:
            return self.asset
        if self.application and self.application.category_remote_app:
            return self.application.get_remote_app_asset()

    @lazyproperty
    def cmd_filter_rules(self):
        from assets.models import CommandFilterRule
        kwargs = {
            'user_id': self.user.id,
            'system_user_id': self.system_user.id,
        }
        if self.asset:
            kwargs['asset_id'] = self.asset.id
        elif self.application:
            kwargs['application_id'] = self.application_id
        rules = CommandFilterRule.get_queryset(**kwargs)
        return rules

    def load_system_user_auth(self):
        if self.asset:
            self.system_user.load_asset_more_auth(self.asset.id, self.user.username, self.user.id)
        elif self.application:
            self.system_user.load_app_more_auth(self.application.id, self.user.username, self.user.id)


class TempToken(models.JMSModel):
    username = models.CharField(max_length=128, verbose_name=_("Username"))
    secret = models.CharField(max_length=64, verbose_name=_("Secret"))
    verified = models.BooleanField(default=False, verbose_name=_("Verified"))
    date_verified = models.DateTimeField(null=True, verbose_name=_("Date verified"))
    date_expired = models.DateTimeField(verbose_name=_("Date expired"))

    class Meta:
        verbose_name = _("Temporary token")

    @property
    def user(self):
        from users.models import User
        return User.objects.filter(username=self.username).first()

    @property
    def is_valid(self):
        not_expired = self.date_expired and self.date_expired > timezone.now()
        return not self.verified and not_expired


class SuperConnectionToken(ConnectionToken):
    class Meta:
        proxy = True
        verbose_name = _("Super connection token")
