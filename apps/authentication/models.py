import uuid

from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from rest_framework.authtoken.models import Token
from orgs.mixins.models import OrgModelMixin

from common.db import models


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


class ConnectionToken(OrgModelMixin, models.JMSModel):
    class Type(models.TextChoices):
        asset = 'asset', _('Asset')
        application = 'application', _('Application')

    type = models.CharField(
        max_length=16, default=Type.asset, choices=Type.choices, verbose_name=_("Type")
    )
    secret = models.CharField(max_length=64, default='', verbose_name=_("Secret"))
    date_expired = models.DateTimeField(null=True, verbose_name=_("Date expired"))

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
        verbose_name = _('Connection token')
        permissions = [
            ('view_connectiontokensecret', _('Can view connection token secret'))
        ]

    @classmethod
    def get_default_date_expired(cls):
        return datetime.now() + timedelta(seconds=settings.CONNECTION_TOKEN_EXPIRATION)


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
