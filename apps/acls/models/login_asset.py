
from django.db import models
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.models import OrgModelMixin
from .base import BaseACL


class LoginAssetACL(BaseACL, OrgModelMixin):
    class ActionChoices(models.TextChoices):
        login_confirm = 'login_confirm', _('Login confirm')

    # 条件
    users = models.JSONField(verbose_name=_('User'))
    system_users = models.JSONField(verbose_name=_('System User'))
    assets = models.JSONField(verbose_name=_('Asset'))
    # 动作
    action = models.CharField(
        max_length=64, choices=ActionChoices.choices, default=ActionChoices.login_confirm,
        verbose_name=_('Action')
    )
    # 动作: 附加字段
    # - login_confirm
    reviewers = models.ManyToManyField(
        'users.User', related_name='review_login_asset_confirm_acl', blank=True,
        verbose_name=_("Reviewers")
    )
