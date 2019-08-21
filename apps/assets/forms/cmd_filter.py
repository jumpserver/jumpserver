# -*- coding: utf-8 -*-
#
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
import re

from orgs.mixins.forms import OrgModelForm
from ..models import CommandFilter, CommandFilterRule

__all__ = ['CommandFilterForm', 'CommandFilterRuleForm']


class CommandFilterForm(OrgModelForm):
    class Meta:
        model = CommandFilter
        fields = ['name', 'comment']


class CommandFilterRuleForm(OrgModelForm):
    invalid_pattern = re.compile(r'[\.\*\+\[\\\?\{\}\^\$\|\(\)\#\<\>]')

    class Meta:
        model = CommandFilterRule
        fields = [
            'filter', 'type', 'content', 'priority', 'action', 'comment'
        ]
        widgets = {
            'content':  forms.Textarea(attrs={
                'placeholder': 'eg:\r\nreboot\r\nrm -rf'
            }),
        }

    def clean_content(self):
        content = self.cleaned_data.get("content")
        if self.invalid_pattern.search(content):
            invalid_char = self.invalid_pattern.pattern.replace('\\', '')
            msg = _("Content should not be contain: {}").format(invalid_char)
            raise ValidationError(msg)
        return content
