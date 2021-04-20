
from django.db import models
from django.utils.translation import ugettext_lazy as _
from .base import BaseACL, BaseACLQuerySet
from ..utils import contains_ip


class ACLManager(models.Manager):

    def valid(self):
        return self.get_queryset().valid()


class LoginACL(BaseACL):
    class ActionChoices(models.TextChoices):
        reject = 'reject', _('Reject')
        allow = 'allow', _('Allow')

    # 条件
    ip_group = models.JSONField(default=list, verbose_name=_('Login IP'))
    # 动作
    action = models.CharField(
        max_length=64, choices=ActionChoices.choices, default=ActionChoices.reject,
        verbose_name=_('Action')
    )
    # 关联
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='login_acls', verbose_name=_('User')
    )

    objects = ACLManager.from_queryset(BaseACLQuerySet)()

    class Meta:
        ordering = ('priority', '-date_updated', 'name')

    def __str__(self):
        return self.name

    @property
    def action_reject(self):
        return self.action == self.ActionChoices.reject

    @property
    def action_allow(self):
        return self.action == self.ActionChoices.allow

    @staticmethod
    def allow_user_to_login(user, ip):
        acl = user.login_acls.valid().first()
        if not acl:
            return True
        is_contained = contains_ip(ip, acl.ip_group)
        if acl.action_allow and is_contained:
            return True
        if acl.action_reject and not is_contained:
            return True
        return False
