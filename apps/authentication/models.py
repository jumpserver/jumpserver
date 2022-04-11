import uuid

from django.utils.translation import ugettext_lazy as _
from rest_framework.authtoken.models import Token
from django.conf import settings

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


class ConnectionToken(models.JMSModel):
    class Types(models.TextChoices):
        asset = 'asset', 'Asset'
        app = 'app', 'App'

    secret = models.CharField(max_length=64, verbose_name=_("Secret"))
    user = models.CharField(max_length=36, verbose_name=_("User id"))
    user_display = models.CharField(max_length=128, verbose_name=_("User display"))
    system_user = models.CharField(max_length=36, verbose_name=_("System user"))
    system_user_display = models.CharField(max_length=128, verbose_name=_("System user display"))
    asset = models.CharField(max_length=36, verbose_name=_("Asset"))
    asset_display = models.CharField(max_length=128, verbose_name=_("Asset display"))
    type = models.CharField(max_length=16, choices=Types.choices, verbose_name=_("Type"))
    date_expired = models.DateTimeField(verbose_name=_("Datetime expired"))

    class Meta:
        verbose_name = _('Connection token')
        permissions = [
            ('view_connectiontokensecret', _('Can view connection token secret'))
        ]


class SuperConnectionToken(ConnectionToken):
    class Meta:
        proxy = True
        verbose_name = _("Super connection token")
