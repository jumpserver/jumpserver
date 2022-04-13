import uuid

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from rest_framework.authtoken.models import Token

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


class ConnectionToken(models.JMSBaseModel):
    # Todo: 未来可能放到这里，不记录到 redis 了，虽然方便，但是不易于审计
    # Todo: add connection token 可能要授权给 普通用户, 或者放开就行

    class Meta:
        verbose_name = _('Connection token')
        permissions = [
            ('view_connectiontokensecret', _('Can view connection token secret'))
        ]


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
