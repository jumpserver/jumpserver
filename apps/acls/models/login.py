
from django.db import models
from django.utils.translation import ugettext_lazy as _
from .base import BaseACL


class LoginACL(BaseACL):
    class ActionChoices(models.TextChoices):
        reject = 'reject', _('Reject')

    # 条件
    ip_group = models.JSONField(default=list, verbose_name=_('Login IP'))
    # 动作
    action = models.CharField(
        max_length=64, choices=ActionChoices.choices, default=ActionChoices.reject,
        verbose_name=_('Action')
    )
    # 关联
    users = models.ManyToManyField('users.User', related_name='login_acl', verbose_name=_('User'))
