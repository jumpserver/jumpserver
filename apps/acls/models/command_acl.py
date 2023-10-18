# -*- coding: utf-8 -*-
#
import re

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils import lazyproperty, get_logger
from orgs.mixins.models import JMSOrgBaseModel
from .base import UserAssetAccountBaseACL

logger = get_logger(__file__)


class TypeChoices(models.TextChoices):
    command = 'command', _('Command')
    regex = 'regex', _('Regex')


class CommandGroup(JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    type = models.CharField(
        max_length=16, default=TypeChoices.command, choices=TypeChoices.choices,
        verbose_name=_("Type")
    )
    content = models.TextField(verbose_name=_("Content"), help_text=_("One line one command"))
    ignore_case = models.BooleanField(default=True, verbose_name=_('Ignore case'))

    TypeChoices = TypeChoices

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Command group")

    @lazyproperty
    def pattern(self):
        if self.type == 'command':
            s = self.construct_command_regex(self.content)
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

    def match(self, data):
        succeed, error, pattern = self.compile_regex(self.pattern, self.ignore_case)
        if not succeed:
            return False, ''

        found = pattern.search(data)
        if not found:
            return False, ''
        else:
            return True, found.group()

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

    def __str__(self):
        return '{} % {}'.format(self.name, self.type)


class CommandFilterACL(UserAssetAccountBaseACL):
    command_groups = models.ManyToManyField(
        CommandGroup, verbose_name=_('Command group'),
        related_name='command_filters'
    )

    class Meta(UserAssetAccountBaseACL.Meta):
        abstract = False
        verbose_name = _('Command acl')

    def __str__(self):
        return self.name

    def create_command_review_ticket(self, run_command, session, cmd_filter_acl, org_id):
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
            'apply_from_cmd_filter_acl_id': str(cmd_filter_acl.id),
            'org_id': org_id,
        }
        ticket = ApplyCommandTicket.objects.create(**data)
        assignees = self.reviewers.all()
        ticket.open_by_system(assignees)
        return ticket
