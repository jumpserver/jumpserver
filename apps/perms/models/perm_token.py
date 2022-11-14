from django.db import models
from django.utils.translation import gettext_lazy as _


class PermToken(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    account = models.CharField(max_length=128, verbose_name=_('Account'))
    secret = models.CharField(max_length=1024, verbose_name=_('Secret'))
    protocol = models.CharField(max_length=32, verbose_name=_('Protocol'))
    connect_method = models.CharField(max_length=32, verbose_name=_('Connect method'))

    class Meta:
        abstract = True
