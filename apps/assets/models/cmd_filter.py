# -*- coding: utf-8 -*-
#
import uuid
import re

from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _

from users.models import User, UserGroup
from applications.models import Application
from ..models import SystemUser, Asset, Node

from common.utils import lazyproperty, get_logger, get_object_or_none
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
        verbose_name=_("Nodes")
    )
    assets = models.ManyToManyField(
        'assets.Asset', related_name='cmd_filters', blank=True,
        verbose_name=_("Asset")
    )
    system_users = models.ManyToManyField(
        'assets.SystemUser', related_name='cmd_filters', blank=True,
        verbose_name=_("System user"))
    applications = models.ManyToManyField(
        'applications.Application', related_name='cmd_filters', blank=True,
        verbose_name=_("Application")
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    comment = models.TextField(blank=True, default='', verbose_name=_("Comment"))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
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

    @lazyproperty
    def pattern(self):
        if self.type == 'command':
            s = self.construct_command_regex(content=self.content)
        else:
            s = r'{0}'.format(self.content)

        return s

    @classmethod
    def construct_command_regex(cls, content):
        regex = []
        content = content.replace('\r\n', '\n')
        for _cmd in content.split('\n'):
            cmd = re.sub(r'\s+', ' ', _cmd)
            cmd = re.escape(cmd)
            cmd = cmd.replace('\\ ', '\s+')

            # 有空格就不能 铆钉单词了
            if ' ' in _cmd:
                regex.append(cmd)
                continue

            if not cmd:
                continue

            # 如果是单个字符
            if cmd[-1].isalpha():
                regex.append(r'\b{0}\b'.format(cmd))
            else:
                regex.append(r'\b{0}'.format(cmd))
        s = r'{}'.format('|'.join(regex))
        return s

    @staticmethod
    def compile_regex(regex, ignore_case):
        try:
            if ignore_case:
                pattern = re.compile(regex, re.IGNORECASE)
            else:
                pattern = re.compile(regex)
        except Exception as e:
            error = _('The generated regular expression is incorrect: {}').format(str(e))
            logger.error(error)
            return False, error, None
        return True, '', pattern

    def match(self, data):
        succeed, error, pattern = self.compile_regex(self.pattern, self.ignore_case)
        if not succeed:
            return self.ACTION_UNKNOWN, ''

        found = pattern.search(data)
        if not found:
            return self.ACTION_UNKNOWN, ''

        if self.action == self.ActionChoices.allow:
            return self.ActionChoices.allow, found.group()
        else:
            return self.ActionChoices.deny, found.group()

    def __str__(self):
        return '{} % {}'.format(self.type, self.content)

    def create_command_confirm_ticket(self, run_command, session, cmd_filter_rule, org_id):
        from tickets.const import TicketType
        from tickets.models import ApplyCommandTicket
        data = {
            'title': _('Command confirm') + ' ({})'.format(session.user),
            'type': TicketType.command_confirm,
            'applicant': session.user_obj,
            'apply_run_user_id': session.user_id,
            'apply_run_asset': str(session.asset),
            'apply_run_system_user_id': session.system_user_id,
            'apply_run_command': run_command[:4090],
            'apply_from_session_id': str(session.id),
            'apply_from_cmd_filter_rule_id': str(cmd_filter_rule.id),
            'apply_from_cmd_filter_id': str(cmd_filter_rule.filter.id),
            'org_id': org_id,
        }
        ticket = ApplyCommandTicket.objects.create(**data)
        assignees = self.reviewers.all()
        ticket.open_by_system(assignees)
        return ticket

    @classmethod
    def get_queryset(cls, user_id=None, user_group_id=None, system_user_id=None,
                     asset_id=None, node_id=None, application_id=None, org_id=None):
        # user & user_group
        user_groups = []
        user = get_object_or_none(User, pk=user_id)
        if user:
            user_groups.extend(list(user.groups.all()))
        user_group = get_object_or_none(UserGroup, pk=user_group_id)
        if user_group:
            org_id = user_group.org_id
            user_groups.append(user_group)

        # asset & node
        nodes = []
        asset = get_object_or_none(Asset, pk=asset_id)
        if asset:
            nodes.extend(asset.get_all_nodes())
        node = get_object_or_none(Node, pk=node_id)
        if node:
            org_id = node.org_id
            nodes.extend(list(node.get_ancestors(with_self=True)))

        system_user = get_object_or_none(SystemUser, pk=system_user_id)
        application = get_object_or_none(Application, pk=application_id)
        q = Q()
        if user:
            q |= Q(users=user)
        if user_groups:
            q |= Q(user_groups__in=set(user_groups))
        if system_user:
            org_id = system_user.org_id
            q |= Q(system_users=system_user)
        if asset:
            org_id = asset.org_id
            q |= Q(assets=asset)
        if nodes:
            q |= Q(nodes__in=set(nodes))
        if application:
            org_id = application.org_id
            q |= Q(applications=application)
        if q:
            cmd_filters = CommandFilter.objects.filter(q).filter(is_active=True)
            if org_id:
                cmd_filters = cmd_filters.filter(org_id=org_id)
            rule_ids = cmd_filters.values_list('rules', flat=True)
            rules = cls.objects.filter(id__in=rule_ids)
        else:
            rules = cls.objects.none()
        return rules
