# -*- coding: utf-8 -*-
# @Time    : 2019/11/22 1:49 下午
# @Author  : Alex
# @Email   : 1374462869@qq.com
# @Project : jumpserver
# @File    : models.py

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField

class OIDCUser(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='oidc_user')
    username = models.CharField(max_length=255, unique=True, verbose_name=_('Subject identifier'))
    userinfo = JSONField(verbose_name=_('Subject extra data'))

    class Meta:
        verbose_name = _('OpenID Connect user')
        verbose_name_plural = _('OpenID Connect users')

    def __str__(self):
        return str(self.user)

