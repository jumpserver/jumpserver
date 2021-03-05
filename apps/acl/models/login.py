
from django.db import models
from django.utils.translation import ugettext_lazy as _
from .base import BaseACL


class LoginACL(BaseACL):

    class ActionChoices(models.TextChoices):
        reject = 'reject', _('Reject')

    users = models.ManyToManyField('users.User', related_name='login_acl', verbose_name=_('User'))

    ip_group = models.JSONField(default=list, verbose_name=_('Login IP'))

    action = models.CharField(
        max_length=64, choices=ActionChoices.choices, default=ActionChoices.reject,
        verbose_name=_('Action')
    )
