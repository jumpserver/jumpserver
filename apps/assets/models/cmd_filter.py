# -*- coding: utf-8 -*-
#
import uuid
import re

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _

from orgs.mixins import OrgModelMixin


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
        verbose_name = _("Command filter")


class CommandFilterRule(OrgModelMixin):
    TYPE_REGEX = 'regex'
    TYPE_COMMAND = 'command'
    TYPE_CHOICES = (
        (TYPE_REGEX, _('Regex')),
        (TYPE_COMMAND, _('Command')),
    )

    ACTION_DENY, ACTION_ALLOW, ACTION_UNKNOWN = range(3)
    ACTION_CHOICES = (
        (ACTION_DENY, _('Deny')),
        (ACTION_ALLOW, _('Allow')),
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    filter = models.ForeignKey('CommandFilter', on_delete=models.CASCADE, verbose_name=_("Filter"), related_name='rules')
    type = models.CharField(max_length=16, default=TYPE_COMMAND, choices=TYPE_CHOICES, verbose_name=_("Type"))
    priority = models.IntegerField(default=50, verbose_name=_("Priority"), help_text=_("1-100, the higher will be match first"),
                                   validators=[MinValueValidator(1), MaxValueValidator(100)])
    content = models.TextField(max_length=1024, verbose_name=_("Content"), help_text=_("One line one command"))
    action = models.IntegerField(default=ACTION_DENY, choices=ACTION_CHOICES, verbose_name=_("Action"))
    comment = models.CharField(max_length=64, blank=True, default='', verbose_name=_("Comment"))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Created by'))

    __pattern = None

    class Meta:
        ordering = ('-priority', 'action')
        verbose_name = _("Command filter rule")

    @property
    def _pattern(self):
        if self.__pattern:
            return self.__pattern
        if self.type == 'command':
            regex = []
            for cmd in self.content.split('\r\n'):
                cmd = cmd.replace(' ', '\s+')
                regex.append(r'\b{0}\b'.format(cmd))
            self.__pattern = re.compile(r'{}'.format('|'.join(regex)))
        else:
            self.__pattern = re.compile(r'{0}'.format(self.content))
        return self.__pattern

    def match(self, data):
        found = self._pattern.search(data)
        if not found:
            return self.ACTION_UNKNOWN, ''

        if self.action == self.ACTION_ALLOW:
            return self.ACTION_ALLOW, found.group()
        else:
            return self.ACTION_DENY, found.group()

    def __str__(self):
        return '{} % {}'.format(self.type, self.content)
