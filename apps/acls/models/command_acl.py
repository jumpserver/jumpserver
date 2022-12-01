# -*- coding: utf-8 -*-
#
import re

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from users.models import User, UserGroup
from orgs.mixins.models import JMSOrgBaseModel
from common.utils import lazyproperty, get_logger, get_object_or_none
from orgs.mixins.models import OrgModelMixin
from .base import BaseACL

logger = get_logger(__file__)


class CommandGroup(JMSOrgBaseModel):
    class Type(models.TextChoices):
        command = 'command', _('Command')
        regex = 'regex', _('Regex')

    name = models.CharField(max_length=128, verbose_name=_("Name"))
    type = models.CharField(max_length=16, default=Type.command, choices=Type.choices, verbose_name=_("Type"))
    content = models.TextField(verbose_name=_("Content"), help_text=_("One line one command"))
    ignore_case = models.BooleanField(default=True, verbose_name=_('Ignore case'))

    class Meta:
        unique_together = [('org_id', 'name')]
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
        args = []
        if ignore_case:
            args.append(re.IGNORECASE)
        try:
            pattern = re.compile(regex, *args)
        except Exception as e:
            error = _('The generated regular expression is incorrect: {}').format(str(e))
            logger.error(error)
            return False, error, None
        return True, '', pattern

    def match(self, data):
        succeed, error, pattern = self.compile_regex(self.pattern, self.ignore_case)
        if not succeed:
            return False, ''

        found = pattern.search(data)
        if not found:
            return False, ''
        else:
            return True, found.group()

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
            'apply_run_account': str(session.account),
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
    def get_queryset(
            cls, user_id=None, user_group_id=None, account=None,
            asset_id=None, org_id=None
    ):
        from assets.models import Account
        user_groups = []
        user = get_object_or_none(User, pk=user_id)
        if user:
            user_groups.extend(list(user.groups.all()))
        user_group = get_object_or_none(UserGroup, pk=user_group_id)
        if user_group:
            org_id = user_group.org_id
            user_groups.append(user_group)

        asset = get_object_or_none(Asset, pk=asset_id)
        q = Q()
        if user:
            q |= Q(users=user)
        if user_groups:
            q |= Q(user_groups__in=set(user_groups))
        if account:
            org_id = account.org_id
            q |= Q(accounts__contains=account.username) | \
                 Q(accounts__contains=Account.AliasAccount.ALL)
        if asset:
            org_id = asset.org_id
            q |= Q(assets=asset)
        if q:
            cmd_filters = CommandFilter.objects.filter(q).filter(is_active=True)
            if org_id:
                cmd_filters = cmd_filters.filter(org_id=org_id)
            rule_ids = cmd_filters.values_list('rules', flat=True)
            rules = cls.objects.filter(id__in=rule_ids)
        else:
            rules = cls.objects.none()
        return rules


class CommandFilterACL(OrgModelMixin, BaseACL):
    # 条件
    users = models.JSONField(verbose_name=_('User'))
    accounts = models.JSONField(verbose_name=_('Account'))
    assets = models.JSONField(verbose_name=_('Asset'))
    commands = models.ManyToManyField(CommandGroup, verbose_name=_('Commands'))

    class Meta:
        unique_together = ('name', 'org_id')
        ordering = ('priority', '-date_updated', 'name')
        verbose_name = _('Command acl')
