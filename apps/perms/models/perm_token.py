from django.db import models
from django.utils.translation import gettext_lazy as _


class PermToken(models.Model):
    """
    1. 用完失效
    2. 仅用于授权，不用于认证
    3. 存 redis 就行
    4. 有效期 5 分钟
    """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    account = models.CharField(max_length=128, verbose_name=_('Account'))
    secret = models.CharField(max_length=1024, verbose_name=_('Secret'))
    protocol = models.CharField(max_length=32, verbose_name=_('Protocol'))
    connect_method = models.CharField(max_length=32, verbose_name=_('Connect method'))
    actions = models.IntegerField(verbose_name=_('Actions'))

    class Meta:
        abstract = True
