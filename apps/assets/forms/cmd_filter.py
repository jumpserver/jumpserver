# -*- coding: utf-8 -*-
#
from django import forms

from orgs.mixins import OrgModelForm
from ..models import CommandFilter, CommandFilterRule

__all__ = ['CommandFilterForm', 'CommandFilterRuleForm']


class CommandFilterForm(OrgModelForm):
    class Meta:
        model = CommandFilter
        fields = ['name', 'comment']


class CommandFilterRuleForm(OrgModelForm):
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
