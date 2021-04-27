# -*- coding: utf-8 -*-
#
import uuid
import re

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from orgs.mixins.models import OrgModelMixin


__all__ = [
    'CommandFilter', 'CommandFilterRule'
]


class CommandFilter(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=64, verbose_name=_("Name"))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    comment = models.TextField(blank=True, default='', verbose_name=_("Comment"))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Created by'))

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
        allow = 1, _('Allow')
        confirm = 2, _('Reconfirm')

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    filter = models.ForeignKey('CommandFilter', on_delete=models.CASCADE, verbose_name=_("Filter"), related_name='rules')
    type = models.CharField(max_length=16, default=TYPE_COMMAND, choices=TYPE_CHOICES, verbose_name=_("Type"))
    priority = models.IntegerField(default=50, verbose_name=_("Priority"), help_text=_("1-100, the lower the value will be match first"),
                                   validators=[MinValueValidator(1), MaxValueValidator(100)])
    content = models.TextField(verbose_name=_("Content"), help_text=_("One line one command"))
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
    def _pattern(self):
        if self.type == 'command':
            regex = []
            content = self.content.replace('\r\n', '\n')
            for cmd in content.split('\n'):
                cmd = re.escape(cmd)
                cmd = cmd.replace('\\ ', '\s+')
                if cmd[-1].isalpha():
                    regex.append(r'\b{0}\b'.format(cmd))
                else:
                    regex.append(r'\b{0}'.format(cmd))
            s = r'{}'.format('|'.join(regex))
        else:
            s = r'{0}'.format(self.content)
        try:
            _pattern = re.compile(s)
        except:
            _pattern = ''
        return _pattern

    def match(self, data):
        found = self._pattern.search(data)
        if not found:
            return self.ACTION_UNKNOWN, ''

        if self.action == self.ActionChoices.allow:
            return self.ActionChoices.allow, found.group()
        else:
            return self.ActionChoices.deny, found.group()

    def __str__(self):
        return '{} % {}'.format(self.type, self.content)

    def create_command_confirm_ticket(self, run_command, session, cmd_filter_rule, org_id):
        from tickets.const import TicketTypeChoices
        from tickets.models import Ticket
        data = {
            'title': _('Command confirm') + ' ({})'.format(session.user),
            'type': TicketTypeChoices.command_confirm,
            'meta': {
                'apply_run_user': session.user,
                'apply_run_asset': session.asset,
                'apply_run_system_user': session.system_user,
                'apply_run_command': run_command,
                'apply_from_session_id': str(session.id),
                'apply_from_cmd_filter_rule_id': str(cmd_filter_rule.id),
                'apply_from_cmd_filter_id': str(cmd_filter_rule.filter.id)
            },
            'org_id': org_id,
        }
        ticket = Ticket.objects.create(**data)
        ticket.assignees.set(self.reviewers.all())
        ticket.open(applicant=session.user_obj)
        return ticket
