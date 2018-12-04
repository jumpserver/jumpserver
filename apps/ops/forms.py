# -*- coding: utf-8 -*-
#
from django import forms

from .models import CommandExecution


class CommandExecutionForm(forms.ModelForm):
    class Meta:
        model = CommandExecution
        fields = ['run_as', 'cmd']
