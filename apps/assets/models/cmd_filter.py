# -*- coding: utf-8 -*-
#
import uuid

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from orgs.mixins.models import OrgModelMixin

logger = get_logger(__file__)

__all__ = [
    'CommandFilter', 'CommandFilterRule'
]


class CommandFilter(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=64, verbose_name=_("Name"))
    users = models.ManyToManyField(
        'users.User', related_name='cmd_filters', blank=True,
        verbose_name=_("User")
    )
    user_groups = models.ManyToManyField(
        'users.UserGroup', related_name='cmd_filters', blank=True,
        verbose_name=_("User group"),
    )
    nodes = models.ManyToManyField(
        'assets.Node', related_name='cmd_filters', blank=True,
        verbose_name=_("Node")
    )
    assets = models.ManyToManyField(
        'assets.Asset', related_name='cmd_filters', blank=True,
        verbose_name=_("Asset")
    )
    accounts = models.JSONField(default=list, verbose_name=_("Accounts"))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    comment = models.TextField(blank=True, default='', verbose_name=_("Comment"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_('Date updated'))
    created_by = models.CharField(
        max_length=128, blank=True, default='', verbose_name=_('Created by')
    )

    def __str__(self):
        return self.name

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Command filter")


class CommandFilterRule(OrgModelMixin):
    TYPE_REGEX = 'regex'
    TYPE_COMMAND = 'command'
    TYPE_CHOICES = (
        (TYPE_REGEX, _('Regex')),
        (TYPE_COMMAND, _('Command')),
    )

    ACTION_UNKNOWN = 10

    class ActionChoices(models.IntegerChoices):
        deny = 0, _('Deny')
        allow = 9, _('Allow')
        confirm = 2, _('Reconfirm')

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    filter = models.ForeignKey(
        'CommandFilter', on_delete=models.CASCADE, verbose_name=_("Filter"), related_name='rules'
    )
    type = models.CharField(max_length=16, default=TYPE_COMMAND, choices=TYPE_CHOICES, verbose_name=_("Type"))
    priority = models.IntegerField(
        default=50, verbose_name=_("Priority"), help_text=_("1-100, the lower the value will be match first"),
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    content = models.TextField(verbose_name=_("Content"), help_text=_("One line one command"))
    ignore_case = models.BooleanField(default=True, verbose_name=_('Ignore case'))
    action = models.IntegerField(default=ActionChoices.deny, choices=ActionChoices.choices, verbose_name=_("Action"))
    # 动作: 附加字段
    # - confirm: 命令复核人
    reviewers = models.ManyToManyField(
        'users.User', related_name='review_cmd_filter_rules', blank=True,
        verbose_name=_("Reviewers")
    )
    comment = models.CharField(max_length=64, blank=True, default='', verbose_name=_("Comment"))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Created by'))

    class Meta:
        ordering = ('priority', 'action')
        verbose_name = _("Command filter rule")
